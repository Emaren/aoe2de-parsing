import NextAuth, { NextAuthOptions } from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";

export const dynamic = "force-dynamic"; // ✅ Make API route dynamic

// Extend the session type to include steamId
declare module "next-auth" {
  interface Session {
    user: {
      name?: string | null;
      email?: string | null;
      image?: string | null;
      steamId?: string; // ✅ Ensure steamId exists
    };
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    sub?: string; // ✅ Ensure token.sub is a string
  }
}

const authOptions: NextAuthOptions = {
  providers: [
    CredentialsProvider({
      name: "Steam",
      credentials: {
        openid: { label: "OpenID", type: "hidden", value: "http://specs.openid.net/auth/2.0" },
        mode: { label: "Mode", type: "hidden", value: "checkid_setup" },
        claimed_id: { label: "Claimed ID", type: "hidden", value: "http://specs.openid.net/auth/2.0/identifier_select" },
        identity: { label: "Identity", type: "hidden", value: "http://specs.openid.net/auth/2.0/identifier_select" },
        return_to: { label: "Return To", type: "hidden", value: `${process.env.NEXTAUTH_URL}/api/auth/callback/steam` },
        realm: { label: "Realm", type: "hidden", value: process.env.NEXTAUTH_URL || "" },
      },
      async authorize(credentials) {
        if (!credentials) return null;
        return { id: credentials.identity, steamId: credentials.identity }; // ✅ Add steamId explicitly
      },
    }),
  ],
  pages: {
    signIn: "/login",
  },
  callbacks: {
    async session({ session, token }) {
      session.user = { ...session.user, steamId: token.sub ?? "" }; // ✅ Ensure token.sub is a string
      return session;
    },
    async jwt({ token, account }) {
      if (account?.provider === "steam" && account?.id) {
        token.sub = String(account.id); // ✅ Ensure it's explicitly a string
      }
      return token;
    },
  },
  secret: process.env.NEXTAUTH_SECRET,
  debug: process.env.NODE_ENV === "development",
};

const handler = NextAuth(authOptions);

export { handler as GET, handler as POST };
