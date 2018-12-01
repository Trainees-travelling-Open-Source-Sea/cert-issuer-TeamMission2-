import json
import logging

from cert_schema import normalize_jsonld
from cert_schema import validate_v2
from cert_issuer import helpers
from pycoin.serialize import b2h
from cert_issuer.models import CertificateHandler, BatchHandler

from cert_issuer.signer import FinalizableSigner


class CertificateV2Handler(CertificateHandler):
    def get_byte_array_to_issue(self, certificate_metadata):
        certificate_json = self._get_certificate_to_issue(certificate_metadata)
        normalized = normalize_jsonld(certificate_json, detect_unmapped_fields=False)
        return normalized.encode('utf-8')

    def add_proof(self, certificate_metadata, merkle_proof):
        """
        :param certificate_metadata:
        :param merkle_proof:
        :return:
        """
        certificate_json = self._get_certificate_to_issue(certificate_metadata)
        certificate_json['signature'] = merkle_proof

        with open(certificate_metadata.blockchain_cert_file_name, 'w') as out_file:
            out_file.write(json.dumps(certificate_json))

    def _get_certificate_to_issue(self, certificate_metadata):
        with open(certificate_metadata.unsigned_cert_file_name, 'r') as unsigned_cert_file:
            certificate_json = json.load(unsigned_cert_file)
        return certificate_json

class CertificateWebV2Handler(CertificateHandler):
    def get_byte_array_to_issue(self, certificate_json):
        normalized = normalize_jsonld(certificate_json, detect_unmapped_fields=False)
        return normalized.encode('utf-8')

    def add_proof(self, certificate_json, merkle_proof):
        """
        :param certificate_metadata:
        :param merkle_proof:
        :return:
        """
        return merkle_proof

class CertificateBatchWebHandler(BatchHandler):
    def finish_batch(self, tx_id, chain):
        self.proof = next(self.merkle_tree.get_proof_generator(tx_id, chain))

    def get_certificate_generator(self):
        """
        Returns a generator (1-time iterator) of certificates in the batch
        :return:
        """

        for cert in self.certificates_to_issue:
            data_to_issue = self.certificate_handler.get_byte_array_to_issue(cert)
            yield data_to_issue

    def prepare_batch(self):
        """
        Propagates exception on failure
        :return: byte array to put on the blockchain
        """
        
        for cert in self.certificates_to_issue:
            self.certificate_handler.validate_certificate(cert)

        self.merkle_tree.populate(self.get_certificate_generator())
        logging.info('here is the op_return_code data: %s', b2h(self.merkle_tree.get_blockchain_data()))
        return self.merkle_tree.get_blockchain_data()

/* app.py에서 certificate_batch_handler이다 */
class CertificateBatchHandler(BatchHandler):
    """
    Manages a batch of certificates. Responsible for iterating certificates in a consistent order.

    In this case, certificates are initialized as an Ordered Dictionary, and we iterate in insertion order.
    """
    /* issue_certificates.py에서 실행 */
    def pre_batch_actions(self, config):
        self._process_directories(config)
        
    def post_batch_actions(self, config):
        helpers.copy_output(self.certificates_to_issue)
        logging.info('Your Blockchain Certificates are in %s', config.blockchain_certificates_dir)

    /* issue.py에서 배치를 준비를 해주는 부분인듯 하다  */
    def prepare_batch(self):
        """
        Propagates exception on failure
        :return: byte array to put on the blockchain
        """

        # validate batch
        for _, metadata in self.certificates_to_issue.items():
            self.certificate_handler.validate_certificate(metadata)
        
        # sign batch
        /* 사인을 하는 부분 */
        with FinalizableSigner(self.secret_manager) as signer:
            for _, metadata in self.certificates_to_issue.items():
                self.certificate_handler.sign_certificate(signer, metadata)

        /* 만들어진 batch를머클트리에 올리는 부분인 듯 하다 */
        /* self.get_certificate_generator()는 certificates의 정보를 해쉬한 값을 반환한다  */
        /* 머클트리에 certificates의 정보의 해쉬를 추가 */
        self.merkle_tree.populate(self.get_certificate_generator())
        logging.info('here is the op_return_code data: %s', b2h(self.merkle_tree.get_blockchain_data()))
        /* 머클트리의 root의 해쉬를 반환 */
        return self.merkle_tree.get_blockchain_data()

    /* get_byte_array_to_issue는 트랜잭션을 바이트 코드로 바꾸는 부분이다(해쉬된다) 머클트리에 추가되는 내용 */
    def get_certificate_generator(self):
        """
        Returns a generator (1-time iterator) of certificates in the batch
        :return:
        """
        for uid, metadata in self.certificates_to_issue.items():
            data_to_issue = self.certificate_handler.get_byte_array_to_issue(metadata)
            yield data_to_issue

    def finish_batch(self, tx_id, chain):
        proof_generator = self.merkle_tree.get_proof_generator(tx_id, chain)
        for uid, metadata in self.certificates_to_issue.items():
            proof = next(proof_generator)
            self.certificate_handler.add_proof(metadata, proof)
    
    /* pre_batch_action메소드에서 실행 */
    /* 설정파일에서부터 워킹 디렉토리를 설정하는 듯함 */
    def _process_directories(self, config):
        /* 작업 디렉토리 설정 */
        unsigned_certs_dir = config.unsigned_certificates_dir
        signed_certs_dir = config.signed_certificates_dir
        blockchain_certificates_dir = config.blockchain_certificates_dir
        work_dir = config.work_dir
        
        /* 분석부탁 */
        certificates_metadata = helpers.prepare_issuance_batch(
                unsigned_certs_dir,
                signed_certs_dir,
                blockchain_certificates_dir,
                work_dir)

        num_certificates = len(certificates_metadata)

        if num_certificates < 1:
            return None

        /* 로그를 님가는 코드 */
        logging.info('Processing %d certificates under work path=%s', num_certificates, work_dir)
        /* set_certificates_in_batch를 찾을 수 없음 */
        self.set_certificates_in_batch(certificates_metadata)

