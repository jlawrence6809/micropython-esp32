import { createPortal } from 'preact/compat';
import { VNode } from 'preact';

const PORTAL_ROOT_ID = 'portal-root';

export const DialogPortalRoot = () => {
  return <div id={PORTAL_ROOT_ID}></div>;
};

/**
 * A full screen dialog that can be used to display content in a modal.
 */
type FullScreenDialogProps = {
  children: preact.ComponentChild;
  onClose: () => void;
};

/**
 * A full screen dialog that can be used to display content in a modal.
 */
export const FullScreenDialog = ({
  children,
  onClose,
}: FullScreenDialogProps) => {
  return (
    <DialogPortal>
      <div className="FullScreenDialog">
        <div className="inner">
          <div className="close-button" onMouseDown={onClose}>
            <span>❌</span>
          </div>
          {children}
        </div>
      </div>
    </DialogPortal>
  );
};

/**
 * A portal that can be used to render a dialog in a different part of the DOM.
 */
const DialogPortal = ({ children }: { children: VNode<{}> }) => {
  const portalRoot = document.getElementById(PORTAL_ROOT_ID);
  return portalRoot ? createPortal(children, portalRoot) : null;
};
