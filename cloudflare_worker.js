export default {
  async fetch(request) {
    /* ── CORS ────────────────────────────────────────── */
    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "POST",
          "Access-Control-Allow-Headers": "Content-Type",
        },
      });
    }
    if (request.method !== "POST") {
      return new Response("Gravity Webhook Receiver OK", { status: 200 });
    }

    /* ── Config Supabase ─────────────────────────────── */
    const SUPABASE_URL = "https://uyptbypqzfkdsvpdvwyz.supabase.co";
    const SUPABASE_KEY =
      "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InV5cHRieXBxemZrZHN2cGR2d3l6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAxNTA1ODAsImV4cCI6MjA5NTcyNjU4MH0.ZEZxlWA9H0u6iP3IHn97XjqNABUEl3kqVcsecx9GPKg";
    const HEADERS = {
      "Content-Type": "application/json",
      apikey: SUPABASE_KEY,
      Authorization: "Bearer " + SUPABASE_KEY,
    };

    try {
      const body = await request.json();
      const eventType = (
        body.event_type ||
        body.event ||
        body.type ||
        "unknown"
      ).toLowerCase();

      /* ── 1. Logger le webhook brut ─────────────────── */
      await fetch(SUPABASE_URL + "/rest/v1/webhook_logs", {
        method: "POST",
        headers: HEADERS,
        body: JSON.stringify({ event_type: eventType, payload: body }),
      });

      /* ── 2. Traiter les bookings ───────────────────── */
      /*
       * Qweekle envoie UNE activité par webhook (pas la résa complète).
       * Chaque activité a un order_id qui lie les étapes d'un même pack.
       * On stocke chaque activité dans booking_activities.
       * Le dashboard Streamlit regroupe par order_id.
       */
      if (
        body.object === "booking" ||
        eventType.includes("booking")
      ) {
        const isDelete = eventType.includes("deleted");

        if (isDelete) {
          /* Suppression */
          const bookingId = body.id || "";
          if (bookingId) {
            await fetch(
              SUPABASE_URL +
                "/rest/v1/booking_activities?qweekle_booking_id=eq." +
                bookingId,
              { method: "DELETE", headers: HEADERS }
            );
          }
        } else {
          /* Création / mise à jour */
          const row = {
            qweekle_booking_id: body.id || "",
            order_id: body.order_id || "",
            order_item_id: body.order_item_id || "",
            pack_step: body.pack_step || 0,
            label: body.label || "",
            category: body.category || "",
            subcategory: body.subcategory || "",
            location: body.location || "",
            duration: body.duration || 0,
            qty: body.qty || 0,
            start_at: body.start_at || null,
            end_at: body.end_at || null,
            client_firstname: (body.client && body.client.firstname) || "",
            client_lastname: (body.client && body.client.lastname) || "",
            client_email: (body.client && body.client.email) || "",
            client_phone: (body.client && body.client.phone) || "",
            source: body.source || "",
            global_status: body.global_status || "",
            event_type: eventType,
            raw_payload: body,
          };

          /* Upsert par qweekle_booking_id */
          await fetch(SUPABASE_URL + "/rest/v1/booking_activities", {
            method: "POST",
            headers: {
              ...HEADERS,
              Prefer: "resolution=merge-duplicates",
            },
            body: JSON.stringify(row),
          });
        }
      }

      return new Response(JSON.stringify({ success: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    } catch (e) {
      return new Response(JSON.stringify({ error: e.message }), {
        status: 500,
        headers: { "Content-Type": "application/json" },
      });
    }
  },

  async scheduled(event, env, ctx) {
    /* ── Synchro horaire automatique ─────────────────── */
    try {
      const SUPABASE_URL = "https://uyptbypqzfkdsvpdvwyz.supabase.co";
      const SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InV5cHRieXBxemZrZHN2cGR2d3l6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAxNTA1ODAsImV4cCI6MjA5NTcyNjU4MH0.ZEZxlWA9H0u6iP3IHn97XjqNABUEl3kqVcsecx9GPKg";
      const QWEEKLE_API_KEY = "a712eb126838aeb58223d70725227d84";
      const QWEEKLE_BASE_URL = "https://api.qweekle.io/api";
      
      const headers_qweekle = {
        "Authorization": "Bearer " + QWEEKLE_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json"
      };

      const headers_supa = {
        "Content-Type": "application/json",
        apikey: SUPABASE_KEY,
        Authorization: "Bearer " + SUPABASE_KEY,
        Prefer: "resolution=merge-duplicates"
      };

      // 1. Déterminer le nombre de pages (en récupérant la page 1)
      const res1 = await fetch(`${QWEEKLE_BASE_URL}/bookings?page=1&per_page=100`, { headers: headers_qweekle });
      if (!res1.ok) return;
      const data1 = await res1.json();
      
      const meta = data1.metadata || data1.meta || {};
      let totalPages = 1;
      if (meta.pagination && meta.pagination.total_pages) {
          totalPages = meta.pagination.total_pages;
      } else if (meta.total_pages) {
          totalPages = meta.total_pages;
      } else if (meta.last_page) {
          totalPages = meta.last_page;
      }

      // 2. Fetch les 5 dernières pages (les plus récentes)
      const pagesToFetch = Math.min(totalPages, 5);
      const startPage = totalPages - pagesToFetch + 1;

      for (let p = startPage; p <= totalPages; p++) {
        const resP = await fetch(`${QWEEKLE_BASE_URL}/bookings?page=${p}&per_page=100`, { headers: headers_qweekle });
        if (resP.ok) {
          const dataP = await resP.json();
          const bookings = dataP.data || [];
          
          for (const body of bookings) {
            const row = {
              qweekle_booking_id: body.id || "",
              order_id: body.order_id || "",
              order_item_id: body.order_item_id || "",
              pack_step: body.pack_step || 0,
              label: body.label || "",
              category: body.category || "",
              subcategory: body.subcategory || "",
              location: body.location || "",
              duration: body.duration || 0,
              qty: body.qty || 0,
              start_at: body.start_at || null,
              end_at: body.end_at || null,
              client_firstname: (body.client && body.client.firstname) || "",
              client_lastname: (body.client && body.client.lastname) || "",
              client_email: (body.client && body.client.email) || "",
              client_phone: (body.client && body.client.phone) || "",
              source: body.source || "",
              global_status: body.global_status || "",
              event_type: "cron_sync",
              raw_payload: body,
            };

            await fetch(SUPABASE_URL + "/rest/v1/booking_activities", {
              method: "POST",
              headers: headers_supa,
              body: JSON.stringify(row),
            });
          }
        }
      }
    } catch (e) {
      console.error("Cron failed:", e);
    }
  }
};
