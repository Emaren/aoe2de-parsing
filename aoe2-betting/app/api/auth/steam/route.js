import NextAuth from "next-auth";

const authOptions = {
  providers: [
    {
      id: "steam",
      name: "Steam",
      type: "oauth",
      version: "2.0",
      authorization: {
        url: "https://steamcommunity.com/openid/login",
        params: {
          "openid.ns": "http://specs.openid.net/auth/2.0",
          "openid.mode": "checkid_setup",
          "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select",
          "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
          "openid.return_to": `${process.env.NEXTAUTH_URL}/api/auth/callback/steam`,
          "openid.realm": process.env.NEXTAUTH_URL,
        },
      },
      async profile(profile) {
        const steamId = profile.sub;
        return {
          id: steamId,
          name: profile.name || `Steam User ${steamId}`,
          image: `https://steamcdn-a.akamaihd.net/steamcommunity/public/images/avatars/xx/${steamId}.jpg`,
        };
      },
    },
  ],
  pages: {
    signIn: "/login",
  },
  callbacks: {
    async session({ session, token }) {
      session.user.steamId = token.sub;
      return session;
    },
    async jwt({ token, account }) {
      if (account?.provider === "steam" && account?.id) {
        token.sub = account.id;
      }
      return token;
    },
  },
  secret: process.env.NEXTAUTH_SECRET,
  debug: process.env.NODE_ENV === "development",
};

const handler = NextAuth(authOptions);

// Export only the route handlers (GET and POST)
export { handler as GET, handler as POST };
