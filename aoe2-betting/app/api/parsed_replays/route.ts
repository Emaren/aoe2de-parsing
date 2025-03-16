import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic"; // ✅ Make API route dynamic

export async function GET() {
    return NextResponse.json({ message: "Parsed Replays API is working!" });
  }  

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    console.log("Received replay data:", body);

    return NextResponse.json({ message: "Replay received successfully!", data: body });
  } catch (error) {
    console.error("Error processing replay:", error);
    return NextResponse.json({ error: "Failed to process replay" }, { status: 500 });
  }
}
