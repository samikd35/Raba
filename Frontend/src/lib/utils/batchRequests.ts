/**
 * Batch request utilities for optimizing API calls
 * 
 * These utilities help reduce the number of API calls by batching multiple
 * requests together or implementing request coalescing.
 */

interface BatchQueueItem<T> {
  id: string;
  resolve: (value: T) => void;
  reject: (reason: any) => void;
}

/**
 * Creates a batch request handler that collects requests and executes them together
 * 
 * @param batchFn - Function that processes a batch of IDs
 * @param options - Configuration options
 * @returns Function to request individual items
 */
export function createBatchLoader<T>(
  batchFn: (ids: string[]) => Promise<Map<string, T>>,
  options: {
    maxBatchSize?: number;
    batchDelay?: number;
  } = {}
) {
  const {
    maxBatchSize = 50,
    batchDelay = 10, // 10ms delay to collect requests
  } = options;

  let queue: BatchQueueItem<T>[] = [];
  let timer: NodeJS.Timeout | null = null;

  const processBatch = async () => {
    if (queue.length === 0) return;

    const currentBatch = queue.splice(0, maxBatchSize);
    const ids = currentBatch.map(item => item.id);

    try {
      const results = await batchFn(ids);

      currentBatch.forEach(item => {
        const result = results.get(item.id);
        if (result !== undefined) {
          item.resolve(result);
        } else {
          item.reject(new Error(`No result for ID: ${item.id}`));
        }
      });
    } catch (error) {
      currentBatch.forEach(item => item.reject(error));
    }

    // Process remaining items if any
    if (queue.length > 0) {
      timer = setTimeout(processBatch, 0);
    }
  };

  return (id: string): Promise<T> => {
    return new Promise((resolve, reject) => {
      queue.push({ id, resolve, reject });

      // Clear existing timer
      if (timer) {
        clearTimeout(timer);
      }

      // Set new timer or process immediately if batch is full
      if (queue.length >= maxBatchSize) {
        processBatch();
      } else {
        timer = setTimeout(processBatch, batchDelay);
      }
    });
  };
}

/**
 * Request deduplication - ensures same request is not made multiple times
 * 
 * @param requestFn - Function that makes the API request
 * @returns Deduplicated request function
 */
export function deduplicateRequests<T>(
  requestFn: (key: string) => Promise<T>
): (key: string) => Promise<T> {
  const pendingRequests = new Map<string, Promise<T>>();

  return async (key: string): Promise<T> => {
    // Return existing promise if request is already in flight
    if (pendingRequests.has(key)) {
      return pendingRequests.get(key)!;
    }

    // Create new request
    const promise = requestFn(key)
      .then(result => {
        pendingRequests.delete(key);
        return result;
      })
      .catch(error => {
        pendingRequests.delete(key);
        throw error;
      });

    pendingRequests.set(key, promise);
    return promise;
  };
}

/**
 * Batch multiple API calls with a delay between each call
 * Useful for rate-limited APIs
 * 
 * @param requests - Array of request functions
 * @param delayMs - Delay between requests in milliseconds
 * @returns Promise that resolves when all requests complete
 */
export async function batchWithDelay<T>(
  requests: Array<() => Promise<T>>,
  delayMs: number = 100
): Promise<T[]> {
  const results: T[] = [];

  for (let i = 0; i < requests.length; i++) {
    const result = await requests[i]();
    results.push(result);

    // Add delay between requests (except after the last one)
    if (i < requests.length - 1) {
      await new Promise(resolve => setTimeout(resolve, delayMs));
    }
  }

  return results;
}

/**
 * Execute requests in parallel with a concurrency limit
 * 
 * @param requests - Array of request functions
 * @param concurrency - Maximum number of concurrent requests
 * @returns Promise that resolves when all requests complete
 */
export async function batchWithConcurrency<T>(
  requests: Array<() => Promise<T>>,
  concurrency: number = 5
): Promise<T[]> {
  const results: T[] = new Array(requests.length);
  let currentIndex = 0;

  const executeNext = async (): Promise<void> => {
    while (currentIndex < requests.length) {
      const index = currentIndex++;
      try {
        results[index] = await requests[index]();
      } catch (error) {
        // Store error as result
        results[index] = error as any;
      }
    }
  };

  // Create worker promises
  const workers = Array(Math.min(concurrency, requests.length))
    .fill(null)
    .map(() => executeNext());

  await Promise.all(workers);
  return results;
}

/**
 * Chunk an array into smaller arrays
 * Useful for processing large datasets in batches
 * 
 * @param array - Array to chunk
 * @param size - Size of each chunk
 * @returns Array of chunks
 */
export function chunkArray<T>(array: T[], size: number): T[][] {
  const chunks: T[][] = [];
  for (let i = 0; i < array.length; i += size) {
    chunks.push(array.slice(i, i + size));
  }
  return chunks;
}

/**
 * Process array items in batches with a callback
 * 
 * @param items - Items to process
 * @param batchSize - Size of each batch
 * @param processFn - Function to process each batch
 * @returns Promise that resolves when all batches are processed
 */
export async function processBatches<T, R>(
  items: T[],
  batchSize: number,
  processFn: (batch: T[]) => Promise<R>
): Promise<R[]> {
  const chunks = chunkArray(items, batchSize);
  const results: R[] = [];

  for (const chunk of chunks) {
    const result = await processFn(chunk);
    results.push(result);
  }

  return results;
}
