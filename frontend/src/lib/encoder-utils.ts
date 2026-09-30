export type EncoderMode = 'base64' | 'url';
export type EncoderOperation = 'encode' | 'decode';

export function runEncoder(
  input: string,
  mode: EncoderMode,
  operation: EncoderOperation,
): string {
  if (!input) return '';

  if (mode === 'base64') {
    // Keep the tool's existing UTF-8 Base64 behavior while making it testable
    return operation === 'encode'
      ? btoa(unescape(encodeURIComponent(input)))
      : decodeURIComponent(escape(atob(input)));
  }

  return operation === 'encode'
    ? encodeURIComponent(input)
    : decodeURIComponent(input);
}
