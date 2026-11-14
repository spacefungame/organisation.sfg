// Supabase Edge Function : qweekle-proxy
// Garde la clé API Qweekle V3 côté serveur (variables d'environnement Supabase : QWEEKLE_API_KEY, QWEEKLE_TENANT_ID, QWEEKLE_VENTURE_ID)

import { serve } from "https://deno.land/std@0.177.0/http/server.ts";

const QWEEKLE_BASE_URL = Deno.env.get("QWEEKLE_BASE_URL") || "https://api.qweekle.app/api";
const QWEEKLE_API_KEY = Deno.env.get("QWEEKLE_API_KEY") || "";
const QWEEKLE_TENANT_ID = Deno.env.get("QWEEKLE_TENANT_ID") || "01a1bd09-3f36-7167-8fba-193675cd8342";
const QWEEKLE_VENTURE_ID = Deno.env.get("QWEEKLE_VENTURE_ID") || "3de205e0-a995-11ea-b3ea-d537696521c3";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization, apikey, x-client-info",
};

function getQweekleHeaders() {
  return {
    "Authorization": `Bearer ${QWEEKLE_API_KEY}`,
    "tenant": QWEEKLE_TENANT_ID,
    "x-venture-id": QWEEKLE_VENTURE_ID,
    "Accept": "application/json",
  };
}

serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: corsHeaders });
  }

  try {
    const urlObj = new URL(req.url);
    const dateStr = urlObj.searchParams.get("date");
    const endpoint = urlObj.searchParams.get("endpoint");

    if (endpoint) {
      const cleanPath = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
      const res = await fetch(`${QWEEKLE_BASE_URL}${cleanPath}`, {
        headers: getQweekleHeaders(),
      });
      const data = await res.json();
      return new Response(JSON.stringify(data), {
        status: res.status,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    if (!dateStr || !/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
      return new Response(
        JSON.stringify({ error: "Paramètre 'date' (YYYY-MM-DD) requis." }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } },
      );
    }

    const allBookings: any[] = [];
    let offset = 0;
    const limit = 500;
    let hasMore = true;

    while (hasMore) {
      const qUrl = `${QWEEKLE_BASE_URL}/bookings?filter[starts_between]=${dateStr}T00:00:00,${dateStr}T23:59:59&include=client,clientSubs.profile&limit=${limit}&offset=${offset}`;
      const res = await fetch(qUrl, { headers: getQweekleHeaders() });
      if (!res.ok) {
        throw new Error(`Qweekle V3 /bookings returned ${res.status}`);
      }
      const json = await res.json();
      const pageData = Array.isArray(json.data) ? json.data : [];
      allBookings.push(...pageData);
      if (pageData.length < limit) {
        hasMore = false;
      } else {
        offset += limit;
      }
    }

    const activeBookings = allBookings.filter((b) => {
      if (!b || b.deleted_at) return false;
      if (b.activated === false || b.activated === 0 || b.activated === "0") return false;
      const st = String(b.global_status || b.state || "").toLowerCase();
      if (st === "cancelled" || st === "canceled" || st === "deleted" || st === "rejected") return false;
      const cl = b.client || {};
      const hasClient = Boolean(cl.id || cl.lastname || cl.firstname || cl.society || cl.email || b.client_id);
      return hasClient;
    });

    const orderIds = Array.from(new Set(activeBookings.map((b) => b.order_id).filter(Boolean)));
    const ordersMap: Record<string, any> = {};

    await Promise.all(
      orderIds.map(async (oid) => {
        try {
          const oRes = await fetch(`${QWEEKLE_BASE_URL}/orders/${oid}?include=items`, {
            headers: getQweekleHeaders(),
          });
          if (oRes.ok) {
            const oJson = await oRes.json();
            if (oJson && oJson.data) {
              ordersMap[String(oid)] = oJson.data;
            }
          }
        } catch (_e) {
          // ignore individual order fetch error
        }
      }),
    );

    return new Response(
      JSON.stringify({
        status: "ok",
        date: dateStr,
        data: activeBookings,
        orders: ordersMap,
      }),
      { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } },
    );
  } catch (err: any) {
    return new Response(
      JSON.stringify({ error: err.message || "Internal Server Error" }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } },
    );
  }
});
