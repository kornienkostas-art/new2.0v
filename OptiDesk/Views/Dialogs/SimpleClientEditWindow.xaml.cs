using System.Windows;

namespace OptiDesk.Views.Dialogs
{
    public partial class SimpleClientEditWindow : Window
    {
        public string ClientName => NameBox.Text.Trim();
        public string? ClientPhone => PhoneBox.Text.Trim();
        public string? ClientNote => NoteBox.Text.Trim();

        public SimpleClientEditWindow(string? name = null, string? phone = null, string? note = null)
        {
            InitializeComponent();
            NameBox.Text = name ?? "";
            PhoneBox.Text = phone ?? "";
            NoteBox.Text = note ?? "";
        }

        private void Ok_Click(object sender, RoutedEventArgs e)
        {
            if (string.IsNullOrWhiteSpace(ClientName))
            {
                MessageBox.Show("Введите имя клиента.", "Внимание", MessageBoxButton.OK, MessageBoxImage.Warning);
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