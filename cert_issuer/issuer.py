"""
Base class for building blockchain transactions to issue Blockchain Certificates.
"""
import logging

from cert_issuer.errors import BroadcastError

MAX_TX_RETRIES = 5


class Issuer:
    def __init__(self, certificate_batch_handler, transaction_handler, max_retry=MAX_TX_RETRIES):
        self.certificate_batch_handler = certificate_batch_handler
        self.transaction_handler = transaction_handler
        self.max_retry = max_retry

    def issue(self, chain):
        """
        Issue the certificates on the blockchain
        :return:
        """

        /* prepare_batch: certificate_handler에서 certificate_handler 클래스의 함수인듯 하다 */
        /* batch의 내용을 준비해 주는 코드인 듯 하다 */
        /* 확인 결과 머클 트리의 root의 hash를 blockchain_bytes에 넣어주는 듯 함 */
        /* certificationhandler의 prepare_batch -> merkle_tree_generator의 get_blockchain_data를 보면 root를 h2b써서(hash to byte인듯) 바이트형으로 반환? */
        /*  */
        blockchain_bytes = self.certificate_batch_handler.prepare_batch()

        for attempt_number in range(0, self.max_retry):
            try:
                /* bitcoin패키지의 transaction_handler 부분의 issue_transaction일 것이다 */
                /* blockchain_bytes는 배치의 정보이다 */
                txid = self.transaction_handler.issue_transaction(blockchain_bytes)
                self.certificate_batch_handler.finish_batch(txid, chain)
                logging.info('Broadcast transaction with txid %s', txid)
                return txid
            except BroadcastError:
                logging.warning(
                    'Failed broadcast reattempts. Trying to recreate transaction. This is attempt number %d',
                    attempt_number)
        logging.error('All attempts to broadcast failed. Try rerunning issuer.')
        raise BroadcastError('All attempts to broadcast failed. Try rerunning issuer.')
