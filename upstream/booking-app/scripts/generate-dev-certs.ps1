New-Item -ItemType Directory -Force .\infra\nginx\certs

docker run --rm `
  -v "${PWD}/infra/nginx/certs:/certs" `
  alpine:3.20 `
  sh -c "apk add --no-cache openssl >/dev/null && openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout /certs/localhost.key -out /certs/localhost.crt -subj '/CN=localhost' -addext 'subjectAltName=DNS:localhost,IP:127.0.0.1'"