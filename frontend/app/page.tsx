/**
 * Placeholder home page.
 *
 * F0 only proves the pipeline: template CSS, fonts and the API client all
 * reachable. The real homepage is converted from the mirror in F2.
 */
import { listVehicles } from "@/lib/api";

export default async function Home() {
  let vehicles: { id: number; name: string }[] = [];
  let error: string | null = null;

  try {
    vehicles = await listVehicles({ cache: "no-store" });
  } catch (e) {
    error = e instanceof Error ? e.message : "unknown error";
  }

  return (
    <main className="container" style={{ padding: "60px 0" }}>
      <h1 className="heading-44-medium color-brand-1 mb-20">
        Austin Limo Shuttle
      </h1>
      <p className="text-16 color-grey-500 mb-30">
        F0 scaffold — template stylesheet, fonts and API client wired up.
      </p>

      <div className="box-button mb-30">
        <span className="btn btn-brand-1">Template button style</span>
        <i className="fi-rr-car ml-15" style={{ fontSize: 24 }} aria-hidden />
      </div>

      <h2 className="heading-24-medium color-brand-1 mb-15">
        Live data from the Django API
      </h2>
      {error ? (
        <p className="text-16 color-orange">
          API unreachable: {error} — is the Django server running on :8000?
        </p>
      ) : (
        <ul className="text-16 color-grey-500">
          {vehicles.map((v) => (
            <li key={v.id}>{v.name}</li>
          ))}
        </ul>
      )}
    </main>
  );
}
