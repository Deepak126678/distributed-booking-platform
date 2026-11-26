New-Item -ItemType Directory -Force .\infra\nginx\certs

docker run --rm `
  -v "${PWD}/infra/nginx/certs:/certs" `
  alpine:3.20 `
  sh -c "apk add --no-cache openssl >/dev/null && \
         openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
           -keyout /certs/booking.key -out /certs/booking.crt \
           -subj '/CN=booking.test' \
           -addext 'subjectAltName=DNS:booking.test,DNS:localhost,IP:127.0.0.1' && \
         cp /certs/booking.crt /certs/localhost.crt && \
         cp /certs/booking.key /certs/localhost.key"
