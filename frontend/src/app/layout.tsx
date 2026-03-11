import type { Metadata } from "next";
import { Nunito } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/components/auth/AuthProvider";
import { NotificationProvider } from "@/components/notifications/NotificationProvider";

const nunito = Nunito({
  variable: "--font-nunito",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700", "800"],
});

export const metadata: Metadata = {
  title: "STICK Admin - Bot Sofia",
  description: "Panel de administracion del bot Sofia para STICK Alineadores",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es" className={nunito.variable}>
      <body className="antialiased">
        <AuthProvider>
          <NotificationProvider>{children}</NotificationProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
