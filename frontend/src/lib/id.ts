let fallbackCounter = 0;

export function createId(): string {
  const cryptoObject = globalThis.crypto as Crypto | undefined;
  if (cryptoObject && typeof cryptoObject.randomUUID === "function") {
    return cryptoObject.randomUUID();
  }

  // Fallback for insecure contexts (http) or older browsers.
  fallbackCounter = (fallbackCounter + 1) % 0xffff;
  return `${Date.now().toString(16)}-${fallbackCounter.toString(16)}-${Math.random().toString(16).slice(2)}`;
}

