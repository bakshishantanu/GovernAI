import "../landing.css";
import "./budget-owners.css";

import { ScrollProgress } from "../_components/scroll-progress";
import { OwnerNav } from "./_components/owner-nav";
import { OwnerHero } from "./_components/owner-hero";
import { SpendReceipt } from "./_components/spend-receipt";
import { KillSwitchDemo } from "./_components/kill-switch-demo";
import { OwnerAnswers } from "./_components/owner-answers";
import { OwnerCta } from "./_components/owner-cta";

export const metadata = {
  title: "GovernAI for IT & budget owners: what your agents cost, and how to stop one",
  description:
    "Itemised, live spend for every AI agent your teams run, an enforced cap that pauses an agent before it overruns, and a kill switch you can throw yourself.",
};

export default function BudgetOwnersPage() {
  return (
    <div className="landing landing-locked-light">
      <ScrollProgress />
      <OwnerNav />
      <main>
        <OwnerHero />
        <SpendReceipt />
        <KillSwitchDemo />
        <OwnerAnswers />
        <OwnerCta />
      </main>
    </div>
  );
}
