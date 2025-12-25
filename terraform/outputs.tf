output "postgres_connection" {
  description = "Информация о подключении к PostgreSQL"
  value = {
    host     = "localhost"
    port     = 5432
    database = var.postgres_database
    user     = var.postgres_user
  }
}

output "redis_connection" {
  description = "Информация о подключении к Redis"
  value = {
    host = "localhost"
    port = 6379
  }
}

output "prometheus_url" {
  description = "URL для доступа к Prometheus"
  value       = "http://localhost:9090"
}

output "grafana_url" {
  description = "URL для доступа к Grafana"
  value       = "http://localhost:3000"
  sensitive   = false
}

output "grafana_credentials" {
  description = "Учетные данные Grafana"
  value = {
    username = "admin"
    password = var.grafana_admin_password
  }
  sensitive = true
}

