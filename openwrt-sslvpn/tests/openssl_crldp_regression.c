/*
 * CVE-2026-35189 regression using an in-memory TLS client and server.
 * Use the source and build directories of a matching static OpenSSL 3.5.9
 * build. The private header lets the test inspect the peer certificate cache.
 *
 * From the repository root:
 *
 *   cc -I"$OPENSSL_BUILD/include" -I"$OPENSSL_SOURCE/include" \
 *     openwrt-sslvpn/tests/openssl_crldp_regression.c \
 *     "$OPENSSL_BUILD/libssl.a" "$OPENSSL_BUILD/libcrypto.a" \
 *     -pthread -ldl -o /tmp/inode-openssl-crldp-regression
 *   /tmp/inode-openssl-crldp-regression
 */
#include <openssl/bio.h>
#include <openssl/err.h>
#include <openssl/evp.h>
#include <openssl/ssl.h>
#include <openssl/x509v3.h>
#include "crypto/x509.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { distribution_points = 1000 };

#define CHECK(condition) do { \
    if (!(condition)) { \
        fprintf(stderr, "line %d: %s\n", __LINE__, #condition); \
        ERR_print_errors_fp(stderr); \
        exit(1); \
    } \
} while (0)

static X509 *make_cert(EVP_PKEY *key)
{
    X509 *cert = X509_new();
    CRL_DIST_POINTS *points = sk_DIST_POINT_new_null();
    X509_NAME *name;
    char organizational_unit[65];
    int i, certificate_size;

    CHECK(cert && points);
    CHECK(X509_set_version(cert, 2));
    CHECK(ASN1_INTEGER_set(X509_get_serialNumber(cert), 1));
    CHECK(X509_gmtime_adj(X509_getm_notBefore(cert), -3600));
    CHECK(X509_gmtime_adj(X509_getm_notAfter(cert), 3600));
    CHECK(X509_set_pubkey(cert, key));
    name = X509_get_subject_name(cert);
    CHECK(X509_NAME_add_entry_by_txt(name, "CN", MBSTRING_ASC,
          (const unsigned char *)"Synthetic CRLDP peer", -1, -1, 0));
    memset(organizational_unit, 'x', sizeof(organizational_unit) - 1);
    organizational_unit[64] = 0;
    for (i = 0; i < 180; ++i) {
        CHECK(X509_NAME_add_entry_by_txt(name, "OU", MBSTRING_ASC,
              (const unsigned char *)organizational_unit, -1, -1, 0));
    }
    CHECK(X509_set_issuer_name(cert, name));
    for (i = 0; i < distribution_points; ++i) {
        DIST_POINT *point = DIST_POINT_new();
        X509_NAME_ENTRY *entry = X509_NAME_ENTRY_create_by_txt(
            NULL, "CN", MBSTRING_ASC, (const unsigned char *)"crl", -1);
        CHECK(point && entry);
        point->distpoint = DIST_POINT_NAME_new();
        CHECK(point->distpoint);
        point->distpoint->type = 1;
        point->distpoint->name.relativename = sk_X509_NAME_ENTRY_new_null();
        CHECK(point->distpoint->name.relativename);
        CHECK(sk_X509_NAME_ENTRY_push(point->distpoint->name.relativename, entry));
        CHECK(sk_DIST_POINT_push(points, point));
    }
    CHECK(X509_add1_ext_i2d(cert, NID_crl_distribution_points, points, 0, 0));
    sk_DIST_POINT_pop_free(points, DIST_POINT_free);
    CHECK(X509_sign(cert, key, EVP_sha256()) > 0);
    certificate_size = i2d_X509(cert, NULL);
    CHECK(certificate_size > 0 && certificate_size < 100 * 1024);
    return cert;
}

static int drive(SSL *ssl)
{
    int result, error;

    if (SSL_is_init_finished(ssl))
        return 1;
    result = SSL_do_handshake(ssl);
    if (result == 1)
        return 1;
    error = SSL_get_error(ssl, result);
    CHECK(error == SSL_ERROR_WANT_READ || error == SSL_ERROR_WANT_WRITE);
    return 0;
}

static void handshake(EVP_PKEY *key, X509 *cert, int version, int verify)
{
    SSL_CTX *client_context = SSL_CTX_new(TLS_client_method());
    SSL_CTX *server_context = SSL_CTX_new(TLS_server_method());
    SSL *client, *server;
    BIO *client_bio, *server_bio;
    X509 *peer;
    int i, result_client, result_server;

    CHECK(client_context && server_context);
    CHECK(SSL_CTX_set_min_proto_version(client_context, version));
    CHECK(SSL_CTX_set_max_proto_version(client_context, version));
    SSL_CTX_set_verify(client_context, verify ? SSL_VERIFY_PEER : SSL_VERIFY_NONE, NULL);
    if (verify)
        CHECK(X509_STORE_add_cert(SSL_CTX_get_cert_store(client_context), cert));
    CHECK(SSL_CTX_use_certificate(server_context, cert));
    CHECK(SSL_CTX_use_PrivateKey(server_context, key));
    client = SSL_new(client_context);
    server = SSL_new(server_context);
    CHECK(client && server);
    CHECK(BIO_new_bio_pair(&client_bio, 0, &server_bio, 0));
    SSL_set_bio(client, client_bio, client_bio);
    SSL_set_bio(server, server_bio, server_bio);
    SSL_set_connect_state(client);
    SSL_set_accept_state(server);
    for (i = 0; i < 100; ++i) {
        result_client = drive(client);
        result_server = drive(server);
        if (result_client && result_server)
            break;
    }
    CHECK(i < 100);
    if (verify)
        CHECK(SSL_get_verify_result(client) == X509_V_OK);
    else
        CHECK(SSL_get_verify_result(client) == X509_V_ERR_DEPTH_ZERO_SELF_SIGNED_CERT);

    peer = SSL_get1_peer_certificate(client);
    CHECK(peer && peer->crldp != NULL);
    CHECK(sk_DIST_POINT_num(peer->crldp) == distribution_points);
    for (i = 0; i < distribution_points; ++i) {
        DIST_POINT *point = sk_DIST_POINT_value(peer->crldp, i);
        CHECK(point->distpoint->type == 1);
        CHECK(point->distpoint->dpname == NULL);
    }
    printf("%s %s: %d relative CRLDP names left unexpanded (DER %d bytes)\n",
           SSL_get_version(client), verify ? "verify-peer" : "verify-none",
           distribution_points, i2d_X509(peer, NULL));

    X509_free(peer);
    SSL_free(client);
    SSL_free(server);
    SSL_CTX_free(client_context);
    SSL_CTX_free(server_context);
}

int main(void)
{
    EVP_PKEY *key = EVP_EC_gen("P-256");
    X509 *cert;

    printf("OpenSSL compile-time: %s\nOpenSSL runtime: %s\n",
           OPENSSL_VERSION_TEXT, OpenSSL_version(OPENSSL_VERSION));
    CHECK(OpenSSL_version_num() == OPENSSL_VERSION_NUMBER);
    CHECK(key);
    cert = make_cert(key);
    handshake(key, cert, TLS1_2_VERSION, 0);
    handshake(key, cert, TLS1_2_VERSION, 1);
    handshake(key, cert, TLS1_3_VERSION, 0);
    handshake(key, cert, TLS1_3_VERSION, 1);
    X509_free(cert);
    EVP_PKEY_free(key);
    return 0;
}
