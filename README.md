# Load Balancer dengan Docker dan Nginx

Sistem load balancer sederhana menggunakan Docker dan Nginx untuk mendistribusikan traffic ke beberapa web server.

## Struktur Proyek
```
.
├── docker-compose.yml
├── nginx/
│   └── nginx.conf
├── web1/
│   └── index.html
├── web2/
│   └── index.html
└── web3/
    └── index.html
```

## Cara Menjalankan

1. Pastikan Docker dan Docker Compose sudah terinstall di sistem Anda
2. Jalankan perintah berikut di terminal:
   ```bash
   docker-compose up -d
   ```
3. Akses load balancer melalui browser di `http://localhost`

## Fitur
- Load balancing menggunakan metode round-robin
- 3 web server backend
- Konfigurasi Nginx yang dapat disesuaikan
- Jaringan Docker terisolasi

## Cara Menghentikan
Untuk menghentikan semua container, jalankan:
```bash
docker-compose down
``` 