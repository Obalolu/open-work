"use client";

import { motion, type HTMLMotionProps, type Variants } from "framer-motion";
import { cn } from "@/lib/cn";

const fadeIn: Variants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { duration: 0.2 } },
};

const slideUp: Variants = {
  hidden: { opacity: 0, y: 12 },
  show: {
    opacity: 1,
    y: 0,
    transition: { type: "spring", stiffness: 380, damping: 32 },
  },
};

const scaleIn: Variants = {
  hidden: { opacity: 0, scale: 0.96 },
  show: {
    opacity: 1,
    scale: 1,
    transition: { type: "spring", stiffness: 380, damping: 32 },
  },
};

export function FadeIn({
  className,
  ...props
}: HTMLMotionProps<"div"> & { className?: string }) {
  return (
    <motion.div
      variants={fadeIn}
      initial="hidden"
      animate="show"
      className={className}
      {...props}
    />
  );
}

export function SlideUp({
  className,
  ...props
}: HTMLMotionProps<"div"> & { className?: string }) {
  return (
    <motion.div
      variants={slideUp}
      initial="hidden"
      animate="show"
      className={className}
      {...props}
    />
  );
}

export function ScaleIn({
  className,
  ...props
}: HTMLMotionProps<"div"> & { className?: string }) {
  return (
    <motion.div
      variants={scaleIn}
      initial="hidden"
      animate="show"
      className={className}
      {...props}
    />
  );
}

export function StaggerContainer({
  className,
  staggerChildren = 0.04,
  delayChildren = 0.05,
  ...props
}: HTMLMotionProps<"div"> & {
  className?: string;
  staggerChildren?: number;
  delayChildren?: number;
}) {
  return (
    <motion.div
      initial="hidden"
      animate="show"
      variants={{
        hidden: { opacity: 0 },
        show: {
          opacity: 1,
          transition: { staggerChildren, delayChildren },
        },
      }}
      className={className}
      {...props}
    />
  );
}

export { motion, cn };
