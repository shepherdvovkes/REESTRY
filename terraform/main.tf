provider "docker" {
  host = "unix:///var/run/docker.sock"
}

# Docker network для всех контейнеров
resource "docker_network" "reestry_network" {
  name = "reestry-network"
  
  ipam_config {
    subnet = "172.20.0.0/16"
  }
}

# PostgreSQL база данных
resource "docker_image" "postgres" {
  name = "postgres:15-alpine"
}

resource "docker_container" "postgres" {
  name  = "reestry-postgres"
  image = docker_image.postgres.image_id
  
  env = [
    "POSTGRES_DB=${var.postgres_database}",
    "POSTGRES_USER=${var.postgres_user}",
    "POSTGRES_PASSWORD=${var.postgres_password}"
  ]
  
  ports {
    internal = 5432
    external = 5432
  }
  
  volumes {
    host_path      = "${path.cwd}/../data/postgres"
    container_path = "/var/lib/postgresql/data"
  }
  
  networks_advanced {
    name = docker_network.reestry_network.name
  }
  
  restart = "unless-stopped"
  
  healthcheck {
    test     = ["CMD-SHELL", "pg_isready -U ${var.postgres_user}"]
    interval = "10s"
    timeout  = "5s"
    retries  = 5
  }
}

# Redis для кэширования
resource "docker_image" "redis" {
  name = "redis:7-alpine"
}

resource "docker_container" "redis" {
  name  = "reestry-redis"
  image = docker_image.redis.image_id
  
  ports {
    internal = 6379
    external = 6379
  }
  
  volumes {
    host_path      = "${path.cwd}/../data/redis"
    container_path = "/data"
  }
  
  command = ["redis-server", "--appendonly", "yes"]
  
  networks_advanced {
    name = docker_network.reestry_network.name
  }
  
  restart = "unless-stopped"
  
  healthcheck {
    test     = ["CMD", "redis-cli", "ping"]
    interval = "10s"
    timeout  = "3s"
    retries  = 5
  }
}

# Dockerfile для краулера
resource "docker_image" "crawler" {
  name = "reestry-crawler:latest"
  build {
    context    = "${path.cwd}/../"
    dockerfile = "Dockerfile.crawler"
  }
}

# Контейнер краулера
resource "docker_container" "crawler" {
  name  = "reestry-crawler"
  image = docker_image.crawler.image_id
  
  env = [
    "LMSTUDIO_URL=${var.lmstudio_url}",
    "POSTGRES_HOST=reestry-postgres",
    "POSTGRES_PORT=5432",
    "POSTGRES_DB=${var.postgres_database}",
    "POSTGRES_USER=${var.postgres_user}",
    "POSTGRES_PASSWORD=${var.postgres_password}",
    "REDIS_HOST=reestry-redis",
    "REDIS_PORT=6379"
  ]
  
  volumes {
    host_path      = "${path.cwd}/../UkrDeepCrawler"
    container_path = "/app"
  }
  
  volumes {
    host_path      = "${path.cwd}/../data/crawler"
    container_path = "/app/data"
  }
  
  networks_advanced {
    name = docker_network.reestry_network.name
  }
  
  restart = "unless-stopped"
  
  depends_on = [
    docker_container.postgres,
    docker_container.redis
  ]
}

# Dockerfile для обработчика
resource "docker_image" "processor" {
  name = "reestry-processor:latest"
  build {
    context    = "${path.cwd}/../"
    dockerfile = "Dockerfile.processor"
  }
}

# Контейнер обработчика
resource "docker_container" "processor" {
  name  = "reestry-processor"
  image = docker_image.processor.image_id
  
  env = [
    "POSTGRES_HOST=reestry-postgres",
    "POSTGRES_PORT=5432",
    "POSTGRES_DB=${var.postgres_database}",
    "POSTGRES_USER=${var.postgres_user}",
    "POSTGRES_PASSWORD=${var.postgres_password}",
    "REDIS_HOST=reestry-redis",
    "REDIS_PORT=6379"
  ]
  
  volumes {
    host_path      = "${path.cwd}/../"
    container_path = "/app"
  }
  
  volumes {
    host_path      = "${path.cwd}/../data/processor"
    container_path = "/app/data"
  }
  
  networks_advanced {
    name = docker_network.reestry_network.name
  }
  
  restart = "unless-stopped"
  
  depends_on = [
    docker_container.postgres,
    docker_container.redis
  ]
}

# Prometheus для мониторинга
resource "docker_image" "prometheus" {
  name = "prom/prometheus:latest"
}

resource "docker_container" "prometheus" {
  name  = "reestry-prometheus"
  image = docker_image.prometheus.image_id
  
  ports {
    internal = 9090
    external = 9090
  }
  
  volumes {
    host_path      = "${path.cwd}/prometheus/prometheus.yml"
    container_path = "/etc/prometheus/prometheus.yml"
  }
  
  volumes {
    host_path      = "${path.cwd}/../data/prometheus"
    container_path = "/prometheus"
  }
  
  command = [
    "--config.file=/etc/prometheus/prometheus.yml",
    "--storage.tsdb.path=/prometheus"
  ]
  
  networks_advanced {
    name = docker_network.reestry_network.name
  }
  
  restart = "unless-stopped"
}

# Grafana для визуализации
resource "docker_image" "grafana" {
  name = "grafana/grafana:latest"
}

resource "docker_container" "grafana" {
  name  = "reestry-grafana"
  image = docker_image.grafana.image_id
  
  ports {
    internal = 3000
    external = 3000
  }
  
  env = [
    "GF_SECURITY_ADMIN_USER=admin",
    "GF_SECURITY_ADMIN_PASSWORD=${var.grafana_admin_password}",
    "GF_USERS_ALLOW_SIGN_UP=false"
  ]
  
  volumes {
    host_path      = "${path.cwd}/../data/grafana"
    container_path = "/var/lib/grafana"
  }
  
  volumes {
    host_path      = "${path.cwd}/grafana/dashboards"
    container_path = "/etc/grafana/provisioning/dashboards"
  }
  
  volumes {
    host_path      = "${path.cwd}/grafana/datasources"
    container_path = "/etc/grafana/provisioning/datasources"
  }
  
  networks_advanced {
    name = docker_network.reestry_network.name
  }
  
  restart = "unless-stopped"
  
  depends_on = [
    docker_container.prometheus
  ]
}

