using System;

namespace OptiDesk.Models
{
    public class OrderMeridian
    {
        public int Id { get; set; }
        public string ClientName { get; set; } = string.Empty;

        // Specific to Meridian supplier/line
        public string Supplier { get; set; } = "Меридиан";
        public string LensType { get; set; } = string.Empty;

        // Placeholder for special fields that differ from MKL orders
        public string? SpecialFields { get; set; }

        public string Status { get; set; } = "Новый";
        public DateTime CreatedAt { get; set; } = DateTime.Now;
        public string? Comment { get; set; }
    }
}