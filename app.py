#!/usr/bin/python3
import json
from flask import Flask, jsonify, request, abort
from subprocess import call

import cert_issuer.config
from cert_issuer.blockchain_handlers import bitcoin
import cert_issuer.issue_certificates

app = Flask(__name__)
config = None

def get_config():
    global config
    if config == None:
        config = cert_issuer.config.get_config()
    return config

@app.route('/cert_issuer/api/v1.0/issue', methods=['POST'])
def issue():
    config = get_config()
    certificate_batch_handler, transaction_handler, connector = \
            bitcoin.instantiate_blockchain_handlers(config, False)
    /* json에는 certificates의 정보가 들어 있고, certificates의 정보를 batch로 만들어 certificate_batch_handler에 넣어주는듯 하다 */
    /* models.py에 set_certificates_in_batch가 정의되어 있다 */
    /* model.py에는 추상메소드가 정의도어있는것 같다 */
    certificate_batch_handler.set_certificates_in_batch(request.json)
    /* certificate_batch_handler에 대해 pre_batch_action을 수행 */
    /* transaction_handler에 대해 ensure_balance를 수행 */
    /* handler의 정보를 넣은 issuer를 생성하고 블록체인에 연결(issue) */
    /* post_batch_action을 수행 */
    cert_issuer.issue_certificates.issue(config, certificate_batch_handler, transaction_handler)
    return json.dumps(certificate_batch_handler.proof)

if __name__ == '__main__':
    app.run()
