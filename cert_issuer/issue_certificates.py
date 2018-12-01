import logging
import sys

from cert_core import Chain

from cert_issuer.issuer import Issuer

if sys.version_info.major < 3:
    sys.stderr.write('Sorry, Python 3.x required by this script.\n')
    sys.exit(1)


def issue(app_config, certificate_batch_handler, transaction_handler):
    /* certificates_handlers.py에 있음 */
    /* unsinged_certs, signed_serts, work directory등 설정을 해준다 */
    /* 만약 certificates의 수가 1 미만이면 리턴됨 */
    /* set_certificates_in_batch는 어디있는지 찾지 못하겠음 */
    certificate_batch_handler.pre_batch_actions(app_config)
    
    /* balnce가 맞는지 확인해 주는 부분인듯 */
    /* transaction_cost > balance라면 오류메세지 출력 */
    transaction_handler.ensure_balance()

    issuer = Issuer(
        certificate_batch_handler=certificate_batch_handler,
        transaction_handler=transaction_handler,
        max_retry=app_config.max_retry)
    /* tx_id는 트랜잭션의 아이디이다 */
    /* issue the certificates on the blockchain */
    /* 바로 위에서 issuer를 만들어서 그 내용으로 issue하는 듯 하다 */
    /* issuer.certificates_batch_handler.prepare_batch()수행 */
    tx_id = issuer.issue(app_config.chain)

    certificate_batch_handler.post_batch_actions(app_config)
    return tx_id


def main(app_config):
    chain = app_config.chain
    if chain == Chain.ethereum_mainnet or chain == Chain.ethereum_ropsten:
        from cert_issuer.blockchain_handlers import ethereum
        certificate_batch_handler, transaction_handler, connector = ethereum.instantiate_blockchain_handlers(app_config)
    else:
        from cert_issuer.blockchain_handlers import bitcoin
        certificate_batch_handler, transaction_handler, connector = bitcoin.instantiate_blockchain_handlers(app_config)
    return issue(app_config, certificate_batch_handler, transaction_handler)


if __name__ == '__main__':
    from cert_issuer import config

    try:
        parsed_config = config.get_config()
        tx_id = main(parsed_config)
        if tx_id:
            logging.info('Transaction id is %s', tx_id)
        else:
            logging.error('Certificate issuing failed')
            exit(1)

    except Exception as ex:
        logging.error(ex, exc_info=True)
        exit(1)
