using Microsoft.Data.Sqlite;
using System.IO;

namespace ZakazLinz.Wpf.Services
{
    public class Database
    {
        public string DbPath { get; }

        public Database()
        {
            var exeDir = AppContext.BaseDirectory;
            DbPath = Path.Combine(exeDir, "data.db");
        }

        public SqliteConnection Open()
        {
            var connString = new SqliteConnectionStringBuilder
            {
                DataSource = DbPath,
                Mode = File.Exists(DbPath) ? SqliteOpenMode.ReadWriteCreate : SqliteOpenMode.ReadWriteCreate
            }.ToString();

            var conn = new SqliteConnection(connString);
            conn.Open();
            return conn;
        }
    }
}