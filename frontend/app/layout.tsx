import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";
const bodyFont = localFont({
 src: [{path:"./fonts/Barlow-Regular.ttf",weight:"400"},{path:"./fonts/Barlow-SemiBold.ttf",weight:"600"}],
 variable:"--font-body",display:"swap",
});
const displayFont = localFont({src:"./fonts/BarlowCondensed-Bold.ttf",weight:"700",variable:"--font-display",display:"swap"});
export const metadata: Metadata = { title: "DojoPulse — Your training workspace", description: "One situation. Measured practice. Honest follow-up. A private Tekken research workspace.", icons: {icon:"/icon.svg"} };
export default function Layout({children}:{children:React.ReactNode}) {
 return <html lang="en"><body className={`${bodyFont.variable} ${displayFont.variable}`}>{children}</body></html>;
}
