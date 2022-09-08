# 估值表导入原型

# 代码生成
sqlacodegen mysql+pymysql://qtrw_platodev:QTdev_2021@10.10.23.102:3306/plato_ods --noviews --noindexes --noconstraints --nojoined --tables BUSI_POS_BOND,BUSI_POS_DEPOSIT,BUSI_POS_FUTURE,BUSI_POS_REPO,BUSI_POS_STOCK,BUSI_VAL_ASSET > ./model/mysql_models.py