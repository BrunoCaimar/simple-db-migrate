from test import *
from mssql import *
from pmock import *
import os
import unittest

class MSSQLTest(unittest.TestCase):

    def setUp(self):
        f = open("test.conf", "w")
        f.write("HOST = 'localhost'\nUSERNAME = 'root'\nPASSWORD = ''\nDATABASE = 'migration_test'")
        f.close()

    def tearDown(self):
        os.remove("test.conf")

    def __mock_db_init(self, mssql_driver_mock, db_mock):
        mssql_driver_mock.expects(at_least_once()).method("connect").will(return_value(db_mock))
        db_mock.expects(at_least_once()).method("select_db")

        # create db if not exists
        db_mock.expects(once()).method("execute_non_query").execute_non_query(eq("if not exists ( select 1 from sysdatabases where name = 'migration_test') create database migration_test;"))
        db_mock.expects(once()).method("close")

        # create version table if not exists
        create_version_table = "if not exists (select 1 from sysobjects where name = '__db_version__' and type = 'u') create table __db_version__ ( version varchar(20) NOT NULL default '0' );"
        self.__mock_db_execute(db_mock, create_version_table)

        # check if exists any version
        db_mock.expects(once()).method("execute_scalar").execute_scalar(eq("select count(*) from __db_version__;")).will(return_value("0"));
        db_mock.expects(once()).method("close")

    def __mock_db_execute(self, db_mock, query):
        # mock a call to __execute
        db_mock.expects(once()).method("__mssql_connect")

        sql_statements = query.split(";")
        sql_statements = [s.strip() for s in sql_statements if s.strip() != ""]
        for statement in sql_statements:
            db_mock.expects(once()).method("execute_non_query").execute_non_query(eq(statement))

        db_mock.expects(once()).method("close")

    def test_it_should_create_database_and_version_table_on_init_if_not_exists(self):
        mssql_driver_mock = Mock()
        db_mock = Mock()

        self.__mock_db_init(mssql_driver_mock, db_mock)

        mssql = MSSQL("test.conf", mssql_driver_mock)

    def test_it_should_drop_database_on_init_if_its_asked(self):
        mssql_driver_mock = Mock()
        db_mock = Mock()

        self.__mock_db_init(mssql_driver_mock, db_mock)

        db_mock.expects(once()).method("execute_non_query").execute_non_query(eq("drop database migration_test;"))
        db_mock.expects(once()).method("close")

        mssql = MSSQL(db_config_file="test.conf", mssql_driver=mssql_driver_mock, drop_db_first=True)

    def test_it_should_execute_migration_up_and_update_schema_version(self):
        mssql_driver_mock = Mock()
        db_mock = Mock()

        self.__mock_db_init(mssql_driver_mock, db_mock)
        self.__mock_db_execute(db_mock, "create table spam();")
        self.__mock_db_execute(db_mock, "insert into __db_version__ (version) values ('20090212112104');")

        mssql = MSSQL("test.conf", mssql_driver_mock)
        mssql.change("create table spam();", "20090212112104")

    def test_it_should_execute_migration_down_and_update_schema_version(self):
        mssql_driver_mock = Mock()
        db_mock = Mock()

        self.__mock_db_init(mssql_driver_mock, db_mock)
        self.__mock_db_execute(db_mock, "create table spam();")
        self.__mock_db_execute(db_mock, "delete from __db_version__ where version >= '20090212112104';")

        mssql = MSSQL("test.conf", mssql_driver_mock)
        mssql.change("create table spam();", "20090212112104", False)

    def test_it_should_get_current_schema_version(self):
        mssql_driver_mock = Mock()
        db_mock = Mock()

        self.__mock_db_init(mssql_driver_mock, db_mock)

        db_mock.expects(once()).method("execute_scalar").execute_scalar(eq("select top 1 version from __db_version__ order by version desc ")).will(return_value("0"))
        db_mock.expects(once()).method("close")

        mssql = MSSQL("test.conf", mssql_driver_mock)
        self.assertEquals("0", mssql.get_current_schema_version())

# ToDo: Try to figure out how to do this test
#       _mssql don't have fetchall
#
#    def test_it_should_get_all_schema_versions(self):
#        mssql_driver_mock = Mock()
#        db_mock = Mock()
#
#        self.__mock_db_init(mssql_driver_mock, db_mock)
#
#        expected_versions = []
#        expected_versions.append("0")
#        expected_versions.append("20090211120001")
#        expected_versions.append("20090211120002")
#        expected_versions.append("20090211120003")

#        db_mock.expects(once()).method("execute_query").execute_query(eq("select version from __db_version__ order by version;"))
#        db.expects(once()).method("fetchall").will(return_value(tuple(zip(expected_versions))))
#        db_mock.expects(once()).method("close")

#        mssql = MSSQL("test.conf", mssql_driver_mock)

#        schema_versions = mssql.get_all_schema_versions()
#        self.assertEquals(len(expected_versions), len(schema_versions))
#        for version in schema_versions:
#            self.assertTrue(version in expected_versions)

if __name__ == "__main__":
    unittest.main()
