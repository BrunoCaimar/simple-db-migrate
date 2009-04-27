from cli import CLI
import _mssql
import sys

class MSSQL(object):

    def __init__(self, db_config_file="simple-db-migrate.conf", mssql_driver=_mssql, drop_db_first=False):
        self.__cli = CLI()

        # read configurations
        try:
            f = open(db_config_file, "r")
            exec(f.read())
        except IOError:
            self.__cli.error_and_exit("%s: file not found" % db_config_file)
        else:
            f.close()

        self.__mssql_driver = mssql_driver
        self.__mssql_host = HOST
        self.__mssql_user = USERNAME
        self.__mssql_passwd = PASSWORD
        self.__mssql_db = DATABASE
        self.__version_table = "__db_version__"

        if drop_db_first:
            self._drop_database()

        self._create_database_if_not_exists()
        self._create_version_table_if_not_exists()

    def __mssql_connect(self, connect_using_db_name=True):
        try:
            conn = self.__mssql_driver.connect(server=self.__mssql_host, user=self.__mssql_user, password=self.__mssql_passwd)
            if connect_using_db_name:
                conn.select_db(self.__mssql_db)
            return conn
        except Exception, e:
            self.__cli.error_and_exit("could not connect to database (%s)" % e)

    def __execute(self, sql):
        db = self.__mssql_connect()
        try:
            sql_statements = sql.split(";")
            sql_statements = [s.strip() for s in sql_statements if s.strip() != ""]
            for statement in sql_statements:
                db.execute_non_query(statement)
            db.close()
        except Exception, e:
            self.__cli.error_and_exit("error executing migration (%s)" % e)

    def _drop_database(self):
        db = self.__mssql_connect(False)
        try:
            db.execute_non_query("drop database %s;" % self.__mssql_db)
        except Exception, e:
            self.__cli.error_and_exit("can't drop database '%s'; \n%s" % (self.__mssql_db, e))
        db.close()

    def _create_database_if_not_exists(self):
        db = self.__mssql_connect(False)
        db.execute_non_query("if not exists ( select 1 from sysdatabases where name = '%s') create database %s;" % (self.__mssql_db, self.__mssql_db))
        db.close()

    def _create_version_table_if_not_exists(self):
        # create version table
        sql = "if not exists (select 1 from sysobjects where name = '%s' and type = 'u') create table %s ( version varchar(20) NOT NULL default '0' );" % (self.__version_table, self.__version_table)
        self.__execute(sql)

        # check if there is a register there
        db = self.__mssql_connect()
        count = db.execute_scalar("select count(*) from %s;" % self.__version_table)
        db.close()

        # if there is not a version register, insert one
        if count == 0:
            sql = "insert into %s (version) values ('0');" % self.__version_table
            self.__execute(sql)

    def __change_db_version(self, version, up=True):
        if up:
            # moving up and storing history
            sql = "insert into %s (version) values (\'%s\');" % (self.__version_table, str(version))
        else:
            # moving down and deleting from history
            sql = "delete from %s where version >= \'%s\';" % (self.__version_table, str(version))
        self.__execute(sql)

    def change(self, sql, new_db_version, up=True):
        self.__execute(sql)
        self.__change_db_version(new_db_version, up)

    def get_current_schema_version(self):
        db = self.__mssql_connect()
        version = db.execute_scalar("select top 1 version from %s order by version desc " % self.__version_table) or 0
        db.close()
        return version

    def get_all_schema_versions(self):
        versions = []
        db = self.__mssql_connect()
        db.execute_query("select version from %s order by version;" % self.__version_table)
        all_versions = db
        for version in all_versions:
            versions.append(version['version'])
        db.close()
        versions.sort()
        return versions
