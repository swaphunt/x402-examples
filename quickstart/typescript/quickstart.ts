// One x402 call to SwapHunt. Dry run by default; pass --pay (or X402_PAY=1) to pay.
import { decodePaymentResponseHeader, wrapFetchWithPayment, x402Client } from "@x402/fetch";
import { ExactEvmScheme } from "@x402/evm";
import { privateKeyToAccount } from "viem/accounts";

const URL = "https://x402.swaphunt.dev/v1/market/fear-greed";
const MAX_SPEND = Number(process.env.MAX_SPEND_USD ?? "0.10");
const PAY = process.argv.includes("--pay") || process.env.X402_PAY === "1";

// Unpaid request -> 402. The PAYMENT-REQUIRED header is base64 JSON with the price.
const header = (await fetch(URL)).headers.get("PAYMENT-REQUIRED")!;
const req = JSON.parse(Buffer.from(header, "base64").toString()).accepts[0];
const price = Number(req.amount) / 1e6; // USDC has 6 decimals
console.log(`Price: $${price.toFixed(3)} USDC on ${req.network}, payTo ${req.payTo}`);

if (!PAY) {
  console.log("Dry run: nothing paid. Re-run with --pay to pay.");
  process.exit(0);
}
const stop = (msg: string) => { console.error(msg); process.exit(1); };
if (price > MAX_SPEND) stop(`Price $${price.toFixed(3)} exceeds MAX_SPEND_USD=${MAX_SPEND}. Not paying.`);
if (!process.env.PRIVATE_KEY) stop("Set PRIVATE_KEY (a dedicated wallet with a few dollars of USDC on Base).");

const key = process.env.PRIVATE_KEY!.replace(/^(0x)?/, "0x") as `0x${string}`; // accept keys with or without 0x
const account = privateKeyToAccount(key);
const client = x402Client.fromConfig({
  schemes: [{ network: "eip155:8453", client: new ExactEvmScheme(account) }],
  spendControls: { maxAmountPerPayment: `$${MAX_SPEND}` },
});
const res = await wrapFetchWithPayment(fetch, client)(URL);
console.log(res.status, await res.json());
const { transaction } = decodePaymentResponseHeader(res.headers.get("PAYMENT-RESPONSE")!);
console.log(`This run cost $${price.toFixed(3)} (tx https://basescan.org/tx/${transaction})`);
