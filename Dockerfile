FROM node:22-alpine
WORKDIR /app
COPY package.json ./
RUN npm install --omit=dev --ignore-scripts
COPY server ./server
COPY shared ./shared
COPY public ./public
COPY scripts ./scripts
RUN node scripts/vendor.mjs
ENV PORT=3000
EXPOSE 3000
CMD ["node", "server/index.js"]
