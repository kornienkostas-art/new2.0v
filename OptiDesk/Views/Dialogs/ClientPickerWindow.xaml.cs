using System.Collections.Generic;
using System.Linq;
using System.Windows;
using OptiDesk.Data;
using OptiDesk.Models;

namespace OptiDesk.Views.Dialogs
{
    public partial class ClientPickerWindow : Window
    {
        private readonly OptiDeskDbContext _db = new OptiDeskDbContext();
        private List<Client> _all = new();

        public Client? Selected { get; private set; }

        public ClientPickerWindow()
        {
            InitializeComponent();
            _db.Database.EnsureCreated();
            Load();
        }

        private void Load()
        {
            _all = _db.Clients.OrderBy(c => c.Name).ToList();
            Grid.ItemsSource = _all;
        }

        private void Search_Click(object sender, RoutedEventArgs e)
        {
            var q = (SearchBox.Text ?? "").Trim().ToLowerInvariant();
            if (string.IsNullOrWhiteSpace(q))
            {
                Grid.ItemsSource = _all;
            }
            else
            {
                Grid.ItemsSource = _all.Where(c =>
                    (c.Name ?? "").ToLowerInvariant().Contains(q) ||
                    (c.Phone ?? "").ToLowerInvariant().Contains(q)).ToList();
            }
        }

        private void Add_Click(object sender, RoutedEventArgs e)
        {
            var dlg = new SimpleClientEditWindow();
            if (dlg.ShowDialog() == true)
            {
                var c = new Client { Name = dlg.ClientName, Phone = dlg.ClientPhone, Note = dlg.ClientNote };
                _db.Clients.Add(c);
                _db.SaveChanges();
                Load();
            }
        }

        private void Edit_Click(object sender, RoutedEventArgs e)
        {
            if (Grid.SelectedItem is not Client c) return;
            var dlg = new SimpleClientEditWindow(c.Name, c.Phone, c.Note);
            if (dlg.ShowDialog() == true)
            {
                c.Name = dlg.ClientName;
                c.Phone = dlg.ClientPhone;
                c.Note = dlg.ClientNote;
                _db.Clients.Update(c);
                _db.SaveChanges();
                Load();
            }
        }

        private void Delete_Click(object sender, RoutedEventArgs e)
        {
            var selected = Grid.SelectedItems.Cast<Client>().ToList();
            if (selected.Count == 0) return;
            foreach (var c in selected)
            {
                _db.Clients.Remove(c);
            }
            _db.SaveChanges();
            Load();
        }

        private void Pick_Click(object sender, RoutedEventArgs e)
        {
            Selected = Grid.SelectedItem as Client;
            if (Selected == null)
            {
                MessageBox.Show("Выберите клиента.", "Внимание", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }
            DialogResult = true;
        }

        private void Cancel_Click(object sender, RoutedEventArgs e)
        {
            DialogResult = false;
        }
    }
}