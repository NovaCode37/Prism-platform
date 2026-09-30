export type DeepPartial<T> = {
  [K in keyof T]?: T[K] extends object ? DeepPartial<T[K]> : T[K];
};

export function makeLookup<T>(english: T) {
  return function lookup(messages: DeepPartial<T>, key: string): string {
    const parts = key.split('.');
    let cur: unknown = messages;
    for (const p of parts) {
      if (cur && typeof cur === 'object' && p in (cur as Record<string, unknown>)) {
        cur = (cur as Record<string, unknown>)[p];
      } else {
        if (messages === english) return key;
        return lookup(english, key);
      }
    }
    return typeof cur === 'string' ? cur : (messages === english ? key : lookup(english, key));
  };
}