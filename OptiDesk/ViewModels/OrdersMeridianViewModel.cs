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
    public class OrdersMeridianViewModel : BaseViewModel
    {
        private readonly OptiDeskDbContext _db = new OptiDeskDbContext();
        private readonly AppSettings _settings;

        public ObservableCollection<OrderMeridian> Items { get; set; } = new();
        private OrderMeridian? _selectedItem;
        public OrderMeridian? SelectedItem
        {
            get => _selectedItem;
            set { _selectedItem = value; RaisePropertyChanged(); }
        }

        public OrdersMeridianViewModel()
        {
            _settings = SettingsService.Load();
            _db.Database.EnsureCreated();
            Load();
        }

        public void Load()
        {
            Items = new ObservableCollection<OrderMeridian>(_db.OrdersMeridian.OrderByDescending(o => o.Id).ToList());
            RaisePropertyChanged(nameof(Items));
        }

        public void AddNew()
        {
            var item = new OrderMeridian { Status = "Новый", Supplier = "Меридиан" };
            Items.Insert(0, item);
            SelectedItem = item;
        }

        public void DeleteSelected(System.Collections.IList selected)
        {
            if (selected == null || selected.Count == 0) return;
            var list = selected.Cast<OrderMeridian>().ToList();

            foreach (var s in list)
            {
                Items.Remove(s);
                if (s.Id != 0)
                {
                    _db.OrdersMeridian.Remove(s);
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
                    _db.OrdersMeridian.Add(item);
                }
                else
                {
                    _db.OrdersMeridian.Update(item);
                }
            }
            _db.SaveChanges();
            Load();
        }

        public string ExportTxt()
        {
            var folder = _settings.ExportFolder!;
            Directory.CreateDirectory(folder);
            var filePath = Path.Combine(folder, $"OrdersMeridian_{DateTime.Now:yyyyMMdd_HHmmss}.txt");

            using (var sw = new StreamWriter(filePath, false, System.Text.Encoding.UTF8))
            {
                sw.WriteLine("Id;ClientName;Supplier;LensType;SpecialFields;Status;CreatedAt;Comment");
                foreach (var o in Items)
                {
                    var line = string.Join(';', new[]
                    {
                        o.Id.ToString(),
                        o.ClientName ?? "",
                        o.Supplier ?? "",
                        o.LensType ?? "",
                        o.SpecialFields ?? "",
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