using System;

namespace OptiDesk.Models
{
    public class OrderMKL
    {
        public int Id { get; set; }
        public string ClientName { get; set; } = string.Empty;
        public string Brand { get; set; } = string.Empty;

        // Standard parameters for soft contact lenses, including toric
        public decimal? Sphere { get; set; }
        public decimal? Cylinder { get; set; }
        public int? Axis { get; set; }

        public string Status { get; set; } = "Новый";
        public DateTime CreatedAt { get; set; } = DateTime.Now;
        public string? Comment { get; set; }
    }
}