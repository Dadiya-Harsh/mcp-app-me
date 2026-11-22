import { Card } from "./Card";

export function ErrorBox({ message }: { message?: string }) {
  return (
    <Card>
      <div className="error-box" role="alert">
        <strong>Couldn't load this.</strong>
        {message ?? "Try asking again."}
      </div>
    </Card>
  );
}
