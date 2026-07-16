# Avenity Agentic Audit Service — deploy the x402-payable AI-visibility MCP
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY avenity_agentic_audit_server.py .

# Dan sets these at run time (never baked into the image):
#   AVENITY_WALLET_ADDRESS   your x402 payee wallet
#   AVENITY_X402_NETWORK     base (default) | base-sepolia
#   AVENITY_X402_FACILITATOR facilitator URL
ENV AVENITY_MCP_TRANSPORT=http \
    AVENITY_MCP_HOST=0.0.0.0 \
    AVENITY_MCP_PORT=8080
EXPOSE 8080
CMD ["python", "avenity_agentic_audit_server.py"]
