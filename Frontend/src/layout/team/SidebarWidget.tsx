import React from "react";
import ChangePlan from "../../components/ChangePlan";
export default function SidebarWidget() {
  return (
    <div
      className={`
        mx-auto mb-10 w-full max-w-60 rounded-2xl bg-brand-25 px-4 py-5 text-center dark:bg-white/[0.03]`}
    >
      <h3 className="mb-2 font-semibold text-brand-500 dark:text-white">
        Upgrade Your Subscription 
      </h3>
      <p className="mb-4 text-gray-500 text-theme-sm dark:text-gray-400">
        Upgrade your subscription to get access to all features.
      </p>
      {/* <a
        href="https://tailadmin.com/pricing"
        target="_blank"
        rel="nofollow"
        className="flex items-center justify-center p-3 font-medium text-white rounded-lg bg-brand-500 text-theme-sm hover:bg-brand-600"
      >
        Upgrade
      </a> */}
      <ChangePlan/>
    </div>
  );
}
