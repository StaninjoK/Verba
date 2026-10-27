import type { Metadata } from "next";
import { LandingPage } from "@/components/landing/LandingPage";
import "./landing.css";

export const metadata: Metadata = {
  title: { absolute: "Verba – Local transcription for audio and video" },
  description:
    "Turn interviews, lectures, meetings and podcasts into editable transcripts and subtitles. Processed locally on your own computer.",
};

export default function Home() {
  return <LandingPage />;
}
