{
    "start_row": 1,
    "subject_code_column": "A",
    "subject_code_detail_regex": "^(.{10})\\.(.+)$",
    "positions": {
        "VALUATIONPORTPOSDTL": [
            {
                "default": {
                    "CURRENCY": "CNY",
                    "BUSI_DATE": {
                        "address": "A4",
                        "capture_regex": "日期：(.+)"
                    },					
					 "PRODUCT_CODE": {
                        "address": "A1",
						"capture_regex": "^(\\d{6})"
                    },
					 "PORTFOLIO_CODE": {
                        "address": "A1",
						"capture_regex": "^(\\d{6})"
                    }
					
                },
                "subjects": [
                    {
                        "code": "\\d{4}\\.\\w\\w\\.01",
                        "values": [
                            {
                                "column": "SECU_CODE",
                                "cell": {
									"address": "A",
									"capture_regex": "\\.(\\d{3,}|\\d\\d\\s)"
								}
                            },													
                            {
                                "column": "SYMBOL",
                                "cell": {
									"address": "A",
									"capture_regex": "\\.(\\d{3,}|\\d\\d\\s)"
								}
                            },
                            {
                                "column": "MARKET_CODE",
								"cell": {
									"address": "A",
									"capture_regex": "\\s(\\w+)"
								}
                            },
                            {
                                "column": "SECU_NAME",
                                "cell": "B"
                            },
                            {
                                "column": "HLD_QTY",
                                "cell": "C"
                            },
                            {
                                "column": "UNIT_COST_O",
                                "cell": "D"
                            },
							{
                                "column": "UNIT_COST_L",
                                "cell": "D"
                            },
                            {
                                "column": "HLD_COST_O",
                                "cell": "E"
                            },
							{
                                "column": "HLD_COST_L",
                                "cell": "E"
                            },
							{
                                "column": "COST_NAV_RATE_L",
                                "cell": "F"
                            },
                            {
                                "column": "VALUATION_PRICE",
                                "cell": "G"
                            },
                            {
                                "column": "HLD_MKTV_O",
                                "cell": "H"
                            },
							{
                                "column": "HLD_MKTV_L",
                                "cell": "H"
                            },
							{
                                "column": "MKTV_NAV_RATE_L",
                                "cell": "I"
                            },
                            {
                                "column": "VALUATION_ADD_AMT_L",
                                "cell": "J"
                            }
                        ]
                    },
                    {
                        "code": "1204.01",
                        "values": [
                            {
                                "column": "ACCD_INTEREST_O",
                                "cell": "H"
                            },
							{
                                "column": "ACCD_INTEREST_L",
                                "cell": "I"
                            }
                        ]
                    }
                ]
            }
        ]
    },
    "product": {
        "model": "VALUATIONPORTIND",
        "values": [
		    {
                "column": "BUSI_DATE",
                "cell": {
                    "address": "A4"
                }
            },
            {
                "column": "PRODUCT_CODE",
                "cell": {
                    "address": "A1",
                    "capture_regex": "^(\\d{6})"
                }
            },
            {
                "column": "PORTFOLIO_CODE",
                "cell": {
                    "address": "A1",
                    "capture_regex": "^(\\d{6})"
                }
            },
			{
                "column": "TOTAL_ASSET_MKTV",
                "cell": {
                    "address": "H",
                    "subject_code": "资产合计"
                }
            },
			{
                "column": "TOTAL_ASSET_COST",
                "cell": {
                    "address": "E",
                    "subject_code": "资产合计"
                }
            },
			{
                "column": "TOTAL_LIABILITIES_MKTV",
                "cell": {
                    "address": "H",
                    "subject_code": "负债合计"
                }
            },
			{
                "column": "TOTAL_LIABILITIES_COST",
                "cell": {
                    "address": "E",
                    "subject_code": "负债合计"
                }
            },
			{
                "column": "SHARES",
                "cell": {
                    "address": "E",
                    "subject_code": "实收资本"
                }
            },
			{
                "column": "UNIT_NAV",
                "cell": {
                    "address": "B",
                    "subject_code": "今日单位净值"
                }
            },
			{
                "column": "ACCU_UNIT_NAV",
                "cell": {
                    "address": "B",
                    "subject_code": "累计单位净值"
                }
            },
			{
                "column": "TOTAL_DEPOSIT_AMT",
                "cell": {
                    "address": "E",
                    "subject_code": "1002"
                }
            },
			{
                "column": "CURRENT_DEPOSIT_AMT",
                "cell": {
                    "address": "E",
                    "subject_code": "1002.01"
                }
            },
			{
                "column": "CURRENT_DEPOSIT_AI",
                "cell": {
                    "address": "E",
                    "subject_code": "1204.01"
                }
            },
			{
                "column": "INTEREST_RECEIVABLE",
                "cell": {
                    "address": "E",
                    "subject_code": "1204"
                }
            },
			{
                "column": "CAPITAL_AMT",
                "cell": {
                    "address": "E",
                    "subject_code": "实收资本"
                }
            },
			{
                "column": "PAYABLE_CUSTODIAN_FEE",
                "cell": {
                    "address": "E",
                    "subject_code": "2207"
                }
            }
        ]
    }
}