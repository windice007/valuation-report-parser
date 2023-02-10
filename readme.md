# 估值表导入原型

# 代码生成
sqlacodegen mysql+pymysql://qtrw_platodev:QTdev_2021@10.10.23.102:3306/plato_idx --noviews --noindexes --noconstraints --nojoined --tables VALUATION_PORT_POS_DTL,VALUATION_PORT_IND > ./model/mysql_models.py