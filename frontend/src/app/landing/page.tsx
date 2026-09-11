import "./landing.css";
import { LandingNav } from "./_components/nav";
import { ScrollProgress } from "./_components/scroll-progress";
import { Hero } from "./_components/hero";
import { Problem } from "./_components/problem";
import { Passport } from "./_components/passport";
import { SkillMarketplace } from "./_components/skill-marketplace";
import { Marquee } from "./_components/marquee";
import { HowItWorks } from "./_components/how-it-works";
import { CostGovernance } from "./_components/cost-governance";
import { FeatureGrid, BillingDemoStrip } from "./_components/feature-grid";
import { Personas } from "./_components/personas";
import { FinalCta } from "./_components/final-cta";

export const metadata = {
  title: "GovernAI: Build Agents Fast. Govern Them Faster.",
  description:
    "GovernAI assembles internal AI agents from reusable skills and gives every one an identity, permission scope, and live spending budget at creation.",
};

export default function LandingPage() {
  return (
    <div className="landing landing-locked-light">
      <ScrollProgress />
      <LandingNav />
      <main>
        <Hero />
        <Problem />
        <Passport />
        <SkillMarketplace />
        <Marquee />
        <HowItWorks />
        <CostGovernance />
        <FeatureGrid />
        <BillingDemoStrip />
        <Personas />
        <FinalCta />
      </main>
    </div>
  );
}
