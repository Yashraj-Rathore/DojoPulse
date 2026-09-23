import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = { title: "Performance Lab", description: "One situation. Measured practice. Honest follow-up." };
export default function Layout({children}:{children:React.ReactNode}) {
 return <html lang="en"><body>{children}</body></html>;
}
