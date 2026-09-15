from vrp.base import CaseDict


def test_case_dict_reads_keys_without_case_sensitivity():
    value = CaseDict({"ProductCode": "P1"})
    assert value["productcode"] == "P1"
