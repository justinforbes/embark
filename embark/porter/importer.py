# pylint: disable=C0201
import logging
import csv
import json
import os

from pathlib import Path
import re

from django.conf import settings

from dashboard.models import Vulnerability, Result
from uploader.models import FirmwareAnalysis

logger = logging.getLogger(__name__)


def result_read_in(analysis_id):
    """
    calls read for all files inside csv_logs and stores its contents into the Result model
    :return: success->result_obj fail->None
    """
    logger.debug("starting read-in of %s", analysis_id)
    res = None
    directory = f"{settings.EMBA_LOG_ROOT}/{analysis_id}/emba_logs/csv_logs/"
    csv_list = [os.path.join(directory, file_) for file_ in os.listdir(directory)]
    for file_ in csv_list:
        logger.debug("trying to read: %s", file_)
        if os.path.isfile(file_):      # TODO change check. > if valid EMBA csv file
            logger.debug("File %s found and attempting to read", file_)
            if file_.endswith('f50_base_aggregator.csv'):
                res = f50_csv(file_, analysis_id)
                logger.debug("Result for %s created or updated", analysis_id)
            elif file_.endswith('f20_vul_aggregator.csv'):
                res = f20_csv(file_, analysis_id)
                logger.debug("Result for %s created or updated", analysis_id)
            # TODO license info etc
    return res


def read_csv(path):
    """
    This job reads the csv file
    :return: result_dict
    """
    res_dict = {}
    with open(path, newline='\n', encoding='utf-8') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=';')
        csv_list = []
        for row in csv_reader:
            # remove NAs and other unwanted chars from csv
            if row[-1] == '':
                row.pop(-1)
            if row[-1] == 'NA':
                row.pop(-1)
            csv_list.append(row)
            for ele in csv_list:
                if len(ele) == 2:
                    if not ele[0] in res_dict.keys():
                        res_dict[ele[0]] = ele[1]
                elif len(ele) > 2:
                    if not ele[0] in res_dict.keys():
                        res_dict[ele[0]] = {}
                    if len(ele[2:]) > 1:
                        if not ele[1] in res_dict[ele[0]].keys():
                            res_dict[ele[0]][ele[1]] = {}
                        res_dict[ele[0]][ele[1]][ele[2]] = {ele[_info]: ele[_info + 1] for _info in range(1, len(ele[1:]), 2)}
                    else:
                        res_dict[ele[0]][ele[1]] = ele[2]

    logger.info("result dict: %s", res_dict)
    return res_dict


def f50_csv(file_path, analysis_id):
    """
    return: result object/ None
    """
    logger.debug("starting f50 csv import")
    res_dict = read_csv(path=file_path)

    res_dict.pop('FW_path', None)
    entropy_value = res_dict.get("entropy_value", 0)
    # if type(entropy_value) is str:
    if isinstance(entropy_value, str):
        # entropy_value = re.findall(r'(\d+\.?\d*)', ' 7.55 bits per byte.')[0]
        entropy_value = re.findall(r'(\d+\.?\d*)', entropy_value)[0]
        entropy_value = entropy_value.strip('.')

    res = Result.objects.update_or_create(
        firmware_analysis=FirmwareAnalysis.objects.get(id=analysis_id),
        emba_command=res_dict.get("emba_command", ''),
        architecture_verified=res_dict.get("architecture_verified", ''),
        # os_unverified=res_dict.get("os_unverified", ''),
        os_verified=res_dict.get("os_verified", ''),
        files=int(res_dict.get("files", 0)),
        directories=int(res_dict.get("directories", 0)),
        entropy_value=float(entropy_value),
        shell_scripts=int(res_dict.get("shell_scripts", 0)),
        shell_script_vulns=int(res_dict.get("shell_script_vulns", 0)),
        kernel_modules=int(res_dict.get("kernel_modules", 0)),
        kernel_modules_lic=int(res_dict.get("kernel_modules_lic", 0)),
        interesting_files=int(res_dict.get("interesting_files", 0)),
        post_files=int(res_dict.get("post_files", 0)),
        canary=int(res_dict.get("canary", 0)),
        canary_per=int(res_dict.get("canary_per", 0)),
        relro=int(res_dict.get("relro", 0)),
        relro_per=int(res_dict.get("relro_per", 0)),
        no_exec=int(res_dict.get("no_exec", 0)),
        no_exec_per=int(res_dict.get("no_exec_per", 0)),
        pie=int(res_dict.get("pie", 0)),
        pie_per=int(res_dict.get("pie_per", 0)),
        stripped=int(res_dict.get("stripped", 0)),
        stripped_per=int(res_dict.get("stripped_per", 0)),
        bins_checked=int(res_dict.get("bins_checked", 0)),
        strcpy=int(res_dict.get("strcpy", 0)),
        strcpy_bin=json.dumps(res_dict.get("strcpy_bin", {})),
        versions_identified=int(res_dict.get("versions_identified", 0)),
        cve_high=int(res_dict.get("cve_high", 0)),
        cve_medium=int(res_dict.get("cve_medium", 0)),
        cve_low=int(res_dict.get("cve_low", 0)),
        exploits=int(res_dict.get("exploits", 0)),
        metasploit_modules=int(res_dict.get("metasploit_modules", 0)),
        certificates=int(res_dict.get("certificates", 0)),
        certificates_outdated=int(res_dict.get("certificates_outdated", 0)),
    )
    return res


def f20_csv(file_path, analysis_id=None):
    """
    csv read for f20 (where every line is a CVE)

    return: result object/ None
    """
    logger.debug("starting f20 csv import")
    res_dict = {}
    with open(file_path, newline='\n', encoding='utf-8') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=';')
        next(csv_reader)  # skip first line
        for row in csv_reader:
            try:
                res_dict[row[2]] = {
                    'Binary': row[0],
                    'Version': row[1],
                    'CVSS': row[3],
                    'exploit db exploit available': row[4],
                    'metasploit module': row[5],
                    'trickest PoC': row[6],
                    'Routersploit': row[7],
                    'local exploit': row[8],
                    'remote exploit': row[9],
                    'DoS exploit': row[10],
                    'known exploited vuln': row[11]
                }
            except Exception as error_:
                logger.error("Error in f20 readin: %s", error_)
                logger.error("row got %i memebers", len(row))
        logger.debug("Got the following res_dict: %s", res_dict) 
    res, _ = Result.objects.update_or_create(
        firmware_analysis=FirmwareAnalysis.objects.get(id=analysis_id)
    )
    for key_, value_ in res_dict.items():
        try:
            new_vulnerability = Vulnerability.objects.update_or_create(
                cve=key_,
                info=value_
            )
            logger.debug("Adding Vuln: %s to res %s", new_vulnerability, res)
            res.vulnerability.add(new_vulnerability)
        except Exception as error_:
            logger.error("Error in f20 readin: %s", error_)
    logger.debug("read f20 csv done")
    return res


def f10_csv(_file_path, _analysis_id):
    """
    return: result object/ None
    """
    logger.debug("starting f10 csv import")
    # FIXME needs implementation
    logger.debug("read f10 csv done")


if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    TEST_DIR = os.path.join(BASE_DIR, 'test/porter')

    # test print f50
    with open(os.path.join(TEST_DIR, 'f50_test.json'), 'w', encoding='utf-8') as json_file:
        json_file.write(json.dumps(read_csv(os.path.join(TEST_DIR, 'f50_test.csv')), indent=4))

    # test print f20
    with open(os.path.join(TEST_DIR, 'f20_test.json'), 'w', encoding='utf-8') as json_file:
        json_file.write(json.dumps(
            f20_csv(os.path.join(TEST_DIR, 'f20_test.csv')),
            indent=4
        ))
