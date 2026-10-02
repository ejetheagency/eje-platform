# Railway build for the EJE factory night-shift service. Guarantees Python (the repo also contains a
# Node/Vercel app + public/ static files, which confuse Railway's auto-builder). Vercel ignores this file.
FROM python:3.11-slim
WORKDIR /app
COPY . .
EXPOSE 8080
CMD ["python3", "-m", "factory.service"]
