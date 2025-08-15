import { cn } from '@/lib/utils';

interface CardProps {
  children: React.ReactNode;
  className?: string;
}

interface CardHeaderProps {
  children: React.ReactNode;
  className?: string;
}

interface CardContentProps {
  children: React.ReactNode;
  className?: string;
}

interface CardTitleProps {
  children: React.ReactNode;
  className?: string;
}

function Card({ children, className }: CardProps) {
  return (
    <div className={cn('rounded-lg border border-gray-200 bg-white shadow-sm', className)}>
      {children}
    </div>
  );
}

function CardHeader({ children, className }: CardHeaderProps) {
  return (
    <div className={cn('flex flex-col space-y-1.5 p-6 pb-3', className)}>
      {children}
    </div>
  );
}

function CardTitle({ children, className }: CardTitleProps) {
  return (
    <h3 className={cn('text-lg font-semibold leading-none tracking-tight text-gray-900', className)}>
      {children}
    </h3>
  );
}

function CardContent({ children, className }: CardContentProps) {
  return (
    <div className={cn('p-6 pt-0', className)}>
      {children}
    </div>
  );
}

export { Card, CardHeader, CardTitle, CardContent };
