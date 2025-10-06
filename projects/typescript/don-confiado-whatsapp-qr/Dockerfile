FROM node:20-slim

# Establece el directorio de trabajo
WORKDIR /app

# Instala Git y Python (necesario para compilar algunas dependencias nativas)
RUN apt-get update && apt-get install -y git python3 make g++ && rm -rf /var/lib/apt/lists/*

# Configurar Git para usar HTTPS en lugar de SSH para GitHub
RUN git config --global url."https://github.com/".insteadOf "ssh://git@github.com/"
RUN git config --global url."https://github.com/".insteadOf "git@github.com:"

# Copia el package.json
COPY package.json ./

# Configurar npm para usar HTTPS y timeouts extendidos
RUN npm config set registry https://registry.npmjs.org/
RUN npm config set strict-ssl false

# Instala dependencias con npm (más estable para deps Git)
RUN npm install --verbose

# Copia el código del proyecto
COPY . .

# Expone el puerto
EXPOSE 3000

# Comando por defecto: ejecutar TSX con npx
CMD ["npx", "tsx", "src/index.ts"]