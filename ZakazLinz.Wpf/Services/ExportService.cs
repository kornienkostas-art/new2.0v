using System.IO;
using System.Text;

namespace ZakazLinz.Wpf.Services
{
    public class ExportService
    {
        public void ExportTxt(string filePath, string content)
        {
            var dir = Path.GetDirectoryName(filePath);
            if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
                Directory.CreateDirectory(dir);

            File.WriteAllText(filePath, content, Encoding.UTF8);
        }
    }
}