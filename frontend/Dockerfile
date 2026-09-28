# Frontend image — Next.js 15 dev server.
#
# Node 22 LTS. On Linux the native SWC binary installs cleanly, so the macOS
# .babelrc workaround from the handoff is not needed here.

FROM node:22-slim

ENV NEXT_TELEMETRY_DISABLED=1

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 3000
# Bind to 0.0.0.0 so the port is reachable from the host.
CMD ["npx", "next", "dev", "-H", "0.0.0.0", "-p", "3000"]
