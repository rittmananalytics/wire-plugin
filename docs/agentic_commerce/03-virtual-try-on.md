# Feature: AI Virtual Try-On

## Overview

Allow users to upload a photo of themselves and see how a product would look on them using AI image generation. This creates an engaging, personalised shopping experience that increases purchase confidence and reduces returns.

## Architecture

```
┌──────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  React UI    │────▸│  Edge Function   │────▸│  Image Gen Model    │
│  (Try-On)    │◂────│  /virtual-tryon  │◂────│  (Gemini / DALL-E)  │
└──────────────┘     └──────────────────┘     └─────────────────────┘
       │
       ▼
┌──────────────┐
│  Photo Store │
│  (Storage)   │
└──────────────┘
```

## Implementation Steps

### 1. Photo Upload & Storage

Allow users to upload or capture a photo that will be used for try-on.

```tsx
function PhotoUpload({ onPhotoReady }) {
  const handleFile = async (file: File) => {
    // Resize to reasonable dimensions (e.g. 512x512)
    const resized = await resizeImage(file, 512, 512);

    // Upload to cloud storage
    const { data } = await supabase.storage
      .from("user-photos")
      .upload(`${userId}/${Date.now()}.jpg`, resized);

    // Get public URL
    const url = supabase.storage.from("user-photos").getPublicUrl(data.path);
    onPhotoReady(url);
  };

  return (
    <div>
      <input type="file" accept="image/*" onChange={e => handleFile(e.target.files[0])} />
      <p>Upload a photo to see how this product looks on you</p>
    </div>
  );
}
```

### 2. Try-On Edge Function

Create a backend function that combines the user photo with the product image using AI.

```typescript
// /functions/virtual-tryon
export async function handler(req) {
  const { userPhotoUrl, productImageUrl, productTitle } = await req.json();

  const prompt = `
    Take the person in this photo and show them wearing the "${productTitle}".
    Keep the person's face, body shape, and pose exactly the same.
    Replace or overlay their current clothing with the product shown.
    Maintain realistic lighting, proportions, and fabric draping.
  `;

  // Call multimodal image generation
  const result = await imageModel.generate({
    prompt,
    referenceImages: [
      { url: userPhotoUrl, label: "person" },
      { url: productImageUrl, label: "product" },
    ],
    outputFormat: "png",
    size: "1024x1024",
  });

  // Upload result to storage
  const outputPath = `tryon-results/${crypto.randomUUID()}.png`;
  await storage.upload(outputPath, result.imageBytes);

  return { imageUrl: storage.getPublicUrl(outputPath) };
}
```

### 3. Resilience Pattern

AI image generation is slow and unreliable. Implement robust error handling:

```typescript
async function tryOnWithRetry(params, maxRetries = 3) {
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      const result = await generateTryOn(params);
      return result;
    } catch (err) {
      if (err.status === 429) {
        // Rate limited — exponential backoff
        await sleep(Math.pow(2, attempt) * 1000);
        continue;
      }
      throw err; // Non-retryable error
    }
  }
  throw new Error("Max retries exceeded");
}
```

### 4. React Try-On Component

```tsx
function VirtualTryOn({ product, userPhotoUrl }) {
  const [result, setResult] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleTryOn = async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await supabase.functions.invoke("virtual-tryon", {
        body: {
          userPhotoUrl,
          productImageUrl: product.imageUrl,
          productTitle: product.title,
        },
      });
      setResult(data.imageUrl);
    } catch (err) {
      setError("Try-on failed. You can still add this item to your cart.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      {!result && !loading && (
        <button onClick={handleTryOn}>
          👕 Try this on
        </button>
      )}
      {loading && <LoadingSpinner text="Generating your try-on image..." />}
      {result && <img src={result} alt="Virtual try-on result" />}
      {error && <p className="text-muted-foreground">{error}</p>}
    </div>
  );
}
```

### 5. Timeout Fallback

Set a maximum wait time and gracefully degrade:

```tsx
const TRYON_TIMEOUT = 45000; // 45 seconds

const tryOnWithTimeout = (params) => {
  return Promise.race([
    generateTryOn(params),
    new Promise((_, reject) =>
      setTimeout(() => reject(new Error("timeout")), TRYON_TIMEOUT)
    ),
  ]);
};
```

## Model Options

| Model | Strengths | Limitations |
|-------|-----------|-------------|
| Gemini (Flash Image) | Fast, good at clothing overlay | Occasional artefacts |
| DALL-E 3 | High quality, good instruction following | Expensive, no direct image input |
| Stable Diffusion (img2img) | Self-hostable, customisable | Requires GPU infrastructure |
| Runway ML | Video-capable, realistic | Expensive, API waitlist |

## UX Considerations

- **Loading state** — Show a skeleton or animation; generation takes 5-30 seconds
- **Graceful failure** — Always allow add-to-cart even if try-on fails
- **Photo privacy** — Clearly communicate how photos are stored and used
- **Mobile camera** — Support direct camera capture on mobile devices

## Prompt for Claude Code

```
Add AI Virtual Try-On to this React ecommerce site:

1. Create an edge function at /functions/virtual-tryon that:
   - Accepts { userPhotoUrl, productImageUrl, productTitle }
   - Calls [IMAGE_MODEL] with a compositing prompt
   - Implements retry with exponential backoff for rate limits
   - Uploads the result image to cloud storage
   - Returns { imageUrl } of the generated image

2. Create a VirtualTryOn component that:
   - Shows a "Try this on" button on product cards
   - Displays a loading animation during generation (expect 10-30s)
   - Shows the result image when ready
   - Handles errors gracefully with a fallback message
   - Includes a 45-second timeout with graceful degradation

3. Add photo upload functionality:
   - Allow users to upload or capture a photo
   - Store in cloud storage with proper access controls
   - Remember the user's photo across sessions (localStorage)

4. Integrate into the shopping assistant chat flow.
```
