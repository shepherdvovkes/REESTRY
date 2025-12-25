variable "lmstudio_url" {
  description = "URL для LMStudio API сервера"
  type        = string
  default     = "http://192.168.0.60:1234/v1/chat/completions"
}

variable "postgres_password" {
  description = "Пароль для PostgreSQL"
  type        = string
  default     = "reestry_password"
  sensitive   = true
}

variable "postgres_user" {
  description = "Пользователь PostgreSQL"
  type        = string
  default     = "reestry_user"
}

variable "postgres_database" {
  description = "Имя базы данных PostgreSQL"
  type        = string
  default     = "reestry"
}

variable "grafana_admin_password" {
  description = "Пароль администратора Grafana"
  type        = string
  default     = "admin"
  sensitive   = true
}

