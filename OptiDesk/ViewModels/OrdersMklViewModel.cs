using System;
using System.Collections.ObjectModel;
using System.Globalization;
using System.IO;
using System.Linq;
using OptiDesk.Data;
using OptiDesk.Models;
using OptiDesk.Services;

namespace OptiDesk.ViewModels
{
    public class OrdersMklViewModel : BaseViewModel
    {
        private readonly OptiDeskDbContext _db = new OptiDeskDbContext();
        private readonly AppSettings _settings;

        public ObservableCollection<OrderMKL> Items { get; set; } = new();
        private OrderMKL? _selectedItem;
        public OrderMKL? SelectedItem
        {
            get => _selectedItem;
            set { _selectedItem = value; RaisePropertyChanged(); }
        }

        public OrdersMklViewModel()
        {
            _settings = SettingsService.Load();
            _db.Database.EnsureCreated();
            Load();
        }

        public void Load()
        {
            Items = new ObservableCollection<OrderMKL>(_db.OrdersMKL.OrderByDescending(o => o.Id).ToList());
            RaisePropertyChanged(nameof(Items));
        }

        public void AddNew()
        {
            var item = new OrderMKL { Status = "Новый" };
            Items.Insert(0, item);
            SelectedItem = item;
        }

        public void DeleteSelected(System.Collections.IList selected)
        {
            if (selected == null || selected.Count == 0) return;
            var list = selected.Cast<OrderMKL>().ToList();

            foreach (var s in list)
            {
                Items.Remove(s);
                if (s.Id != 0)
                {
                    _db.OrdersMKL.Remove(s);
                }
            }
            _db.SaveChanges();
        }

        public void SaveAll()
        {
            foreach (var item in Items)
            {
                if (item.Id == 0)
                {
                    _db.OrdersMKL.Add(item);
                }
                else
                {
                    _db.OrdersMKL.Update(item);
                }
            }
            _db.SaveChanges();
            Load();
        }

        public string ExportTxt()
        {
            var folder = _settings.ExportFolder!;
            Directory.CreateDirectory(folder);
            var filePath = Path.Combine(folder, $"OrdersMKL_{DateTime.Now:yyyyMMdd_HHmmss}.txt");

            using (var sw = new StreamWriter(filePath, false, System.Text.Encoding.UTF8))
            {
                sw.WriteLine("Id;ClientName;Brand;Sphere;Cylinder;Axis;Status;CreatedAt;Comment");
                foreach (var o in Items)
                {
                    var line = string.Join(';', new[]
                    {
                        o.Id.ToString(),
                        o.ClientName ?? "",
                        o.Brand ?? "",
                        o.Sphere?.ToString(CultureInfo.InvariantCulture) ?? "",
                        o.Cylinder?.ToString(CultureInfo.InvariantCulture) ?? "",
                        o.Axis?.ToString(CultureInfo.InvariantCulture) ?? "",
                        o.Status ?? "",
                        o.CreatedAt.ToString("s", CultureInfo.InvariantCulture),
                        o.Comment ?? ""
                    });
                    sw.WriteLine(line);
                }
            }
            return filePath;
        }
    }
}