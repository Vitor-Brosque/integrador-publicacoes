export default {
  async fetch(request, env) {
    try {
      if (request.method !== "PUT") {
        return new Response("Method not allowed", { status: 405 });
      }

      const upload_token = request.headers.get("X-Upload-Token");

      if (!env.UPLOAD_TOKEN || upload_token !== env.UPLOAD_TOKEN) {
        return new Response("Unauthorized", { status: 401 });
      }

      const url = new URL(request.url);
      const object_key = decodeURIComponent(url.pathname.replace(/^\/+/, ""));

      if (!object_key) {
        return new Response("Missing object key", { status: 400 });
      }

      const content_type =
        request.headers.get("Content-Type") || "application/octet-stream";

      await env.MEDIA_BUCKET.put(object_key, request.body, {
        httpMetadata: {
          contentType: content_type,
        },
      });

      return Response.json({
        ok: true,
        key: object_key,
      });
    } catch (error) {
      return Response.json(
        {
          ok: false,
          error: String(error),
        },
        { status: 500 }
      );
    }
  },
};
