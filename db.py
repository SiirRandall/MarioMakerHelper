import json
import os
import readline
import sqlite3
import threading
import traceback

class DatabaseError(Exception):
    def __init__(self, message):
        super(DatabaseError, self).__init__(message)

class Connection:
    """Represents an SQL database connection
    
    Parameters
    ----------
    database: Optional[str]
        The local path to the SQLite3 database file. Defaults to `pwd/sqlite3.db`
    verbose: Optional[bool]
        Indicates if verbose mode (deep logging) is used. Defaults to `False`        

    """
    def __init__(self, database:str=None, **kwargs):
        # Try to establish a connection with the database
        self.database = "sqlite3.db" if not database else database
        # This will get the database file name
        self.database_name = "sqlite3.db" if not database else self.database[::-1].split("/")[0][::-1]

        self.commands = [(getattr(self, 'connect'), "?FILE?"),
                         (getattr(self, 'close'), ""),
                         (getattr(self, 'commit'), ""),
                         (getattr(self, 'tables'), ""),
                         (getattr(self, 'path'), ""),
                         (getattr(self, 'execute'), "QUERY"),
                         (getattr(self, 'get'), "?TABLE?"),
                         (getattr(self, 'exit'), ""),
                         (getattr(self, 'interact'), "TABLE"),
                         (getattr(self, 'create'), "NAME COLUMNS"),
                         (getattr(self, 'help'), "?COMMAND?")]

        self.verbose = kwargs.pop('verbose', False)
        self.conn = None

        if self.verbose:
            print("Database initialized!")

    def convert(self, value):
        """Prepare a variable to be inserted with SQL.

        Parameters
        ----------
        value:
            Value to be converted
        """
        # JSON serialize value if it's a list or dict
        # If the value is a string put quotes around it to let SQL know what we're dealing with
        if isinstance(value, list) or isinstance(value, dict):
            value = "'{}'".format(json.dumps(value, separators=(',',':')))
        elif isinstance(value, str):
            value = "'{}'".format(value)
        return str(value)

    def unconvert(self, value):
        """Prepare a variable to be read from SQL.

        Parameters
        ----------
        value:
            Value to be converted
        """
        # Attempt to un-serialize the value
        # If it fails it wasn't a list or dict
        try:
            value = json.loads(value)
        except:
            pass
        return value

    def path(self):
        """Get the path to the database file"""
        if self.database.startswith("/"):
            return self.database
        else:
            return os.getcwd() + "/" + self.database

    def get(self, table:str=None):
        """Fetch a table in the database.

        Parameters
        ----------
        table: str
            The name of the table
        """
        # Fetch all the tables from the database
        selection = self.execute('SELECT name FROM sqlite_master WHERE type=\'table\'', False)
        table_names = selection.fetchall()

        # Create Table objects
        tables = {}
        for name in table_names:
            if table and name[0] == table:
                return Table(self, name[0])
            elif not table:    
                tables[name[0]] = Table(self, name[0])
                
        return tables

    def connect(self, database:str=None):
        """Connect to or create a database at a local path.

        Parameters
        ----------
        database: Optional[str]
            The local path to the SQLite3 database file. Defaults to `self.database`
        """
        database = self.database if not database else database
        self.database = database
        self.database_name = database[::-1].split("/")[0][::-1]
      
        # This will connect to a local database file
        # If it doesn't exist it will create one
        # It will throw an exception if the program has insufficient perms to do so
        try:
            conn = sqlite3.connect(database)
        except Exception:
            traceback.print_exc()
            return None

        print("Connected to sqlite3 database at path {}!".format(database))
        self.conn = conn
    
    def close(self):
        """Close the database connection"""
        if not self.conn:
            raise DatabaseError("No open database connection")

        # Just close the session
        self.conn.close()
        self.conn = None
        print("Closed sqlite3 database connection!")

    def commit(self):
        """Commit pending data to database"""
        if not self.conn:
            raise DatabaseError("No open database connection")

        # Commit the data to the database
        # It will throw an exception if for instance the database file was moved or deleted
        try:
            self.conn.commit()
        except Exception:
            if self.verbose:
                print("Commit failed")
                traceback.print_exc()
            return False

        if self.verbose:
            print("Committed pending data to the database!")

        return True

    def tables(self):
        """Get a list of tables in the database"""
        # Fetch all table names from the database
        selection = self.execute('SELECT name FROM sqlite_master WHERE type=\'table\'', False)
        tables = selection.fetchall()
        return [table[0] for table in tables]

    def execute(self, query:str, commit=True):
        """Execute an SQL query.

        Parameters
        ----------
        query: str
            A string containing the SQL query
        commit: Optional[bool]
            Indicates whether there should be data committed after executing the query
            Defaults to `True`
        """
        if not self.conn:
            raise DatabaseError("No open database connection")

        # Try to execute the sql query and commit
        try:
            result = self.conn.cursor().execute(query)
        except Exception as e:
            if self.verbose:
                print("Query '{}' failed to execute".format(query))
                traceback.print_exc()
            return False
        
        if commit and not self.commit():
            return False

        return result

    def exit(self):
        """Exit the script"""
        os._exit(0)

    def interact(self, table:str):
        """Start an interaction session with a table.

        Parameters
        ----------
        table: str
            The name of the table
        """
        if not self.conn:
            raise DatabaseError("No open database connection")

        # Check if the table is valid
        fetched_table = self.get(table)
        if not fetched_table:
            raise DatabaseError("No table named {} exists".format(table))

        # Start table shell session
        fetched_table.shell()

    def help(self, command:str=None):
        """Display this message"""
        if not command:
            # Get the longest command signature and base the place of the command description on that
            max_length = max([len(command[0].__name__ + " " + command[1]) for command in self.commands])

            for command in self.commands:
                name = command[0].__name__
                signature =  name + " " + command[1]
                print(signature + (max_length - len(signature) + 1) * " " + command[0].__doc__.split(".")[0])
        else:
            # Check if the command is valid
            if command not in [_command[0].__name__ for _command in self.commands]:
                print("-sqlite3: help: no help topics match `{}`. For a list of commands try `help`".format(command))
                return False

            # Print detailed information about command if available
            command = [_command for _command in self.commands if _command[0].__name__ == command][0]
            print("help: {} {}".format(command[0].__name__, command[1]))
            # Strip some whitespace to make it look fancier
            print("    " + command[0].__doc__.replace("        ", "    "))

    def create(self, table:str, columns:dict):
        """Create a table.

        Parameters
        ----------
        table: str
            The name of the table
        columns: dict
            Dictionary of columns to be added to the table
            {'col_name':default_value, 'col_name':default_value etc..}
        """
        if not self.conn:
            raise DatabaseError("No open database connection")

        if not isinstance(columns, dict):
            try:
                columns = json.loads(columns)
            except Exception as e:
                raise DatabaseError("Invalid dictionary passed ({})".format(e))

        # Make the columns SQL-ready
        table_columns = ['\'{}\' DEFAULT {}'.format(column_name, self.convert(default_value)) for column_name, default_value in columns.items()]

        # Create the table
        query = 'CREATE TABLE {} ({})'.format(table, ", ".join(table_columns))

        if self.execute(query):
            if self.verbose:
                print("Created table {} with columns {}".format(table, columns))
            return True
        else:
            return False

    def shell(self):
        """Starts an interactive shell with the database"""
        print("If you want to use spaces in an argument, use a `~` symbol instead")
        print("Enter \"help\" for usage hints.")
        print("Use \"connect ?FILE?\" to connect to a sqlite3 database file.")

        def prompt():
            # Prompt for command and validate data
            query = input("{}> ".format("sqlite3" if not self.conn else self.database_name))

            command = query.partition(" ")
            command_name = command[0] if len(command) > 0 else None
            parameter = command[2] if len(command) >= 2 else None

            if not command_name:
                prompt()
                return

            path = self.path()
            if not os.path.exists(path) and command_name != "connect":
                print("An error occured: The database was either moved or deleted")
                self.close()
                return


            # Check if the command is valid
            if command_name not in [command[0].__name__ for command in self.commands]:
                print("-sqlite3: {}: command not found".format(command_name))
                prompt()
                return

            # Call functions accordingly
            # It will throw an exception if improper parameters have been passed
            # After that recall this function to keep the terminal going
            command = [command for command in self.commands if command[0].__name__ == command_name][0]

            try:
                if command[0].__code__.co_argcount == 1 or parameter == None:
                    response = command[0]()
                elif command[0].__code__.co_argcount == 2:
                    response = command[0](parameter.replace("~", " "))
                elif command[0].__code__.co_argcount == 3:
                    response = command[0](parameter.partition(" ")[0].replace("~", " "), parameter.partition(" ")[2].replace("~", " "))

                # See if the response is 'printable' data
                if not isinstance(response, bool) and response != None:
                    print(response)

            except Exception as e:
                print("An error occured whilst executing command {}: ".format(command_name) + str(e))

            prompt()

        prompt()


class Table:
    """Represents a table in an SQL database

    Parameters
    ----------
    connection: :class:`Connection`
        The SQL database connection object
    name: str
        The name of the table

    """
    def __init__(self, connection:Connection, name:str):
        self.connection = connection
        self.name = name
        self.interact = False
        self.commands = [(getattr(self, 'close'), ""),
                         (getattr(self, 'delete'), "?WHERE?"),
                         (getattr(self, 'path'), ""),
                         (getattr(self, 'clear'), ""),
                         (getattr(self, 'columns'), ""),
                         (getattr(self, 'get'), "?WHERE?"),
                         (getattr(self, 'add'), "ROW ?WHERE?"),
                         (getattr(self, 'drop'), ""),
                         (getattr(self, 'help'), "?COMMAND?")]
                         
        if self.connection.verbose:
            print("Table {} initialized!".format(name))

    def path(self):
        """Get the path to the database file"""
        return os.getcwd() + self.connection.database

    def clear(self):
        """Clear all data from the table"""
        # Remove all row data
        query = 'DELETE FROM {}'.format(self.name)
        
        if self.connection.execute(query):
            if self.connection.verbose:
                print("Cleared table {}!".format(self.name))
            return True
        else:
            return False

    def drop(self):
        """Drop the table"""
        # Remove the table from the database
        self.interact = False
        query = 'DROP TABLE {}'.format(self.name)
        
        if self.connection.execute(query):
            if self.connection.verbose:
                print("Dropped table {}!".format(self.name))
            return True
        else:
            return False

    def delete(self, where:dict):
        """Delete one or more row(s) in a table.
        
        Parameters
        ----------
        where: dict
            Match the rows where specified columns have specified values
            {'col_name':value, 'col_name':value etc..}
        """
        if not isinstance(where, dict):
            try:
                where = json.loads(where)
            except Exception as e:
                raise DatabaseError("Invalid dictionary passed ({})".format(e))

        # Make the where parameter SQL-ready
        where_statements = ["{}={}".format(column, self.connection.convert(value)) for column, value in where.items()]

        # Delete the rows
        query = 'DELETE FROM {} WHERE {}'.format(self.name, " AND ".join(where_statements))

        if self.connection.execute(query):
            if self.connection.verbose:
                print("Deleted row from table {} where {}".format(self.name, where))
            return True
        else:
            return False

    def add(self, row:dict, where:dict=None):
        """Insert/update row data in the table.
                
        Parameters
        ----------
        row: dict
            The row data
            {'col_name':value, 'col_name':value etc..}
        where: Optional[dict]
            Match the rows where specified columns have specified values
            {'col_name':value, 'col_name':value etc..}
        """
        if where and not isinstance(where, dict) or not isinstance(row, dict):
            try:
                row = json.loads(row)
                where = json.loads(where) if where else None
            except Exception as e:
                raise DatabaseError("Invalid dictionary passed ({})".format(e))

        if where:
            # Make the where parameter SQL-ready
            where_statements = ["{}={}".format(column, self.connection.convert(value)) for column, value in where.items()]
        

        # See if the where argument (if passed) is valid
        exists = self.connection.execute('SELECT 1 FROM {} WHERE {}'.format(self.name, " AND ".join(where_statements)), False) if where else False
        if exists:
            # Update the found row
            set_statements = ["{}={}".format(column, self.connection.convert(value)) for column, value in row.items()]

            query = 'UPDATE {} SET {} WHERE {}'.format(self.name, ", ".join(set_statements), " AND ".join(where_statements))

        else:
            # Insert the new row
            values = [self.connection.convert(x) for x in row.values()]
            columns = [x for x in row.keys()]
            
            query = 'INSERT INTO {} ({}) VALUES ({})'.format(self.name, ", ".join(columns), ", ".join(values))

        # Add the data
        if self.connection.execute(query):
            if self.connection.verbose and exists:
                print("Updated row in table {} where {} with data {}".format(self.name, where, row))
            elif self.connection.verbose:
                print("Inserted row into table {} with data {}".format(self.name, row))
            return True
        else:
            return False

    def columns(self):
        """Get a list of columns in the table"""
        selection = self.connection.execute('PRAGMA table_info({})'.format(self.name), False)
        columns = [column for column in selection]
        return [column[1] + ": " + column[4] for column in columns]

    def get(self, where:dict=None):
        """Fetch row data from the table.
                
        Parameters
        ----------
        where: Optional[dict]
            Match the rows where specified columns have specified values
            {'col_name':value, 'col_name':value etc..}
        """
        if not isinstance(where, dict):
            try:
                where = json.loads(where) if where else None
            except Exception as e:
                raise DatabaseError("Invalid dictionary passed ({})".format(e))

        if where:
            # Make the where parameter SQL-ready
            where_statements = ["{}={}".format(column, self.connection.convert(value)) for column, value in where.items()]
    
            # Make a row selection
            selection = self.connection.execute('SELECT * FROM {} WHERE {}'.format(self.name, " AND ".join(where_statements)), False)

        else:
            # Make a row selection
            selection = self.connection.execute('SELECT * FROM {}'.format(self.name), False)

        # Fetch the rows
        rows = [row for row in selection]

        # Retrieve the columns
        selection = self.connection.execute('PRAGMA table_info({})'.format(self.name), False)
        columns = [column for column in selection]

        # Save the column names and values in a list
        table = []
        for row in rows:
            fetched_row = {}
            for column, value in zip(columns, row):
                fetched_row[column[1]] = self.connection.unconvert(value)
            table.append(fetched_row)
            
        if self.connection.verbose and where:
            print("Fetched row from table {} where {}".format(self.name, where))
        elif self.connection.verbose:
            print("Fetched all rows from table {}".format(self.name, where))

        return table

    def close(self):
        """Close the table interaction session"""
        # Just end the session
        self.interact = False
        print("Closed interaction with table {}!".format(self.name))

    def help(self, command:str=None):
        """Display this message"""
        if not command:
            # Get the longest command signature and base the place of the command description on that
            max_length = max([len(command[0].__name__ + " " + command[1]) for command in self.commands])

            for command in self.commands:
                name = command[0].__name__
                signature =  name + " " + command[1]
                print(signature + (max_length - len(signature) + 1) * " " + command[0].__doc__.split(".")[0])
        else:
            # Check if the command is valid
            if command not in [_command[0].__name__ for _command in self.commands]:
                print("-sqlite3: help: no help topics match `{}`. For a list of commands try `help`".format(command))
                return False

            # Print detailed information about command if available
            command = [_command for _command in self.commands if _command[0].__name__ == command][0]
            print("help: {} {}".format(command[0].__name__, command[1]))
            # Strip some whitespace to make it look fancier
            print("    " + command[0].__doc__.replace("        ", "    "))

    def shell(self):
        """Starts an interactive shell with the table"""
        self.interact = True
        print("If you want to use spaces in an argument, use a `~` symbol instead")
        print("Session with table {} started".format(self.name))
        print("Enter \"help\" for usage hints.")

        def prompt():
            # Prompt for command and validate data
            query = input("{}:{}> ".format(self.connection.database_name, self.name))
            command = query.partition(" ")
            command_name = command[0] if len(command) > 0 else None
            parameter = command[2] if len(command) >= 2 else None

            if not command_name:
                prompt()
                return

            # Check if the command is valid
            if command_name not in [command[0].__name__ for command in self.commands]:
                print("-sqlite3: {}: command not found".format(command_name))
                prompt()
                return

            # Call functions accordingly
            # It will throw an exception if improper parameters have been passed
            # After that recall this function to keep the terminal going
            command = [command for command in self.commands if command[0].__name__ == command_name][0]

            try:
                if command[0].__code__.co_argcount == 1 or parameter == None:
                    response = command[0]()
                elif command[0].__code__.co_argcount == 2:
                    response = command[0](parameter.replace("~", " "))
                elif command[0].__code__.co_argcount == 3:
                    response = command[0](parameter.partition(" ")[0].replace("~", " "), parameter.partition(" ")[2].replace("~", " "))
                
                # See if the response is 'printable' data
                if not isinstance(response, bool) and response != None:
                    print(response)

            except Exception as e:
                traceback.print_exc()
                print("An error occured whilst executing command {}: ".format(command_name) + str(e))

            if self.interact:
                prompt()

        prompt()

if __name__ == "__main__":
    c = Connection(verbose=True)
    c.shell()