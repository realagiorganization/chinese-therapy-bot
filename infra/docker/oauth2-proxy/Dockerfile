FROM quay.io/oauth2-proxy/oauth2-proxy:v7.8.1 AS oauth2proxy

FROM caddy:2.9.1-alpine

# Copy binaries/configs
COPY --from=oauth2proxy /bin/oauth2-proxy /usr/local/bin/oauth2-proxy
COPY oauth2-proxy.cfg /etc/oauth2-proxy.cfg
COPY Caddyfile /etc/caddy/Caddyfile
COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

EXPOSE 4180
ENTRYPOINT ["/entrypoint.sh"]
